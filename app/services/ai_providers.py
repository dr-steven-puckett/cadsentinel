from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from abc import ABC, abstractmethod

from openai import OpenAI

logger = logging.getLogger(__name__)

# ============================================================================
# Abstract Provider Interfaces
# ============================================================================

class SummaryProvider(ABC):
    """
    Abstract interface for multimodal drawing summaries.
    """
    model_name: str

    @abstractmethod
    def generate_summary(
        self,
        *,
        document_id: str,
        pdf_path: Optional[Path],
        json_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Return dict:
        {
            "structured_summary": {...},
            "long_form_description": "...",
            "short_description": "...",
            "raw_model_output": {... or str},
        }
        """
        ...


# ======================================================================
# EMBEDDINGS — CORRECTED PROVIDER
# ======================================================================

class EmbeddingProvider:
    """
    Embeds text using OpenAI's text-embedding-3-large (1536 dims).
    Handles batching + sanitization.
    """

    def __init__(
        self,
        client,
        model_name: str = "text-embedding-3-large",
        batch_size: int = 20,
    ):
        self.client = client
        self.model_name = model_name
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Utility: sanitize text (prevent runaway embeddings)
    # ------------------------------------------------------------------
    def _clean_text(self, text: str) -> str:
        text = text.strip()
        if len(text) > 2000:
            # Trim overly long entries that generate huge embeddings
            return text[:2000]
        return text

    # ------------------------------------------------------------------
    # Public: batch embedding
    # ------------------------------------------------------------------
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds many text items in controlled batches.
        Ensures output vectors are exactly 1536 dims.
        """
        cleaned = [self._clean_text(t) for t in texts]

        batches = [
            cleaned[i : i + self.batch_size]
            for i in range(0, len(cleaned), self.batch_size)
        ]

        all_vectors = []

        for batch in batches:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch,
            )

            for item in response.data:
                vec = item.embedding

                # Safety: guarantee correct dimension for pgvector
                if len(vec) != 1536:
                    logger.error(
                        f"Embedding dimension mismatch: expected 1536, got {len(vec)}"
                    )
                    vec = vec[:1536] if len(vec) > 1536 else vec + [0.0] * (1536 - len(vec))

                all_vectors.append(vec)

        return all_vectors

# ============================================================================
# OpenAI Implementations
# ============================================================================

class OpenAISummaryProvider(SummaryProvider):
    """
    Uses GPT-5.1 multimodal API to generate structured summaries.

    Multi-pass design (no JSON truncation):
      1. JSON pass:
         - Serialize full DWG→JSON output
         - Chunk if needed and summarize each chunk
         - Combine chunk summaries into one JSON-based summary

      2. PDF pass:
         - Analyze the drawing PDF only (views, layout, callouts, GD&T frames)

      3. Fusion pass:
         - Merge JSON-based and PDF-based summaries into final structured object
           { structured_summary, long_form_description, short_description }
    """

    def __init__(self, model_name: str = "gpt-5.1"):
        self.model_name = model_name
        self.client = OpenAI()

    # ------------------------------------------------------------------
    # Public API used by ETL
    # ------------------------------------------------------------------
    def generate_summary(
        self,
        *,
        document_id: str,
        pdf_path: Optional[Path],
        json_dict: Dict[str, Any],
    ) -> Dict[str, Any]:

        logger.info("Generating summary for document_id=%s", document_id)

        # 1) Upload PDF once (if present)
        pdf_file_id: Optional[str] = self._upload_pdf(document_id, pdf_path)

        # 2) JSON-only summarization (hierarchical, chunked)
        json_summary = self._summarize_json(document_id, json_dict)

        # 3) PDF-only summarization (if we have a file)
        pdf_summary = ""
        if pdf_file_id:
            pdf_summary = self._summarize_pdf(document_id, pdf_file_id)
        else:
            logger.info(
                "No PDF available for document_id=%s; skipping PDF summarization.",
                document_id,
            )

        # 4) Fusion pass: combine JSON + PDF into final structured object
        fused = self._fuse_summaries(
            document_id=document_id,
            json_summary=json_summary,
            pdf_summary=pdf_summary,
        )

        # If fusion didn't return proper JSON, wrap as text
        if not isinstance(fused, dict):
            logger.warning(
                "Fusion output for document_id=%s was not a dict; wrapping raw text.",
                document_id,
            )
            return {
                "structured_summary": {},
                "long_form_description": str(fused),
                "short_description": None,
                "raw_model_output": fused,
            }

        return {
            "structured_summary": fused.get("structured_summary", {}),
            "long_form_description": fused.get("long_form_description", ""),
            "short_description": fused.get("short_description"),
            "raw_model_output": fused,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_text_from_response(self, response: Any) -> str:
        """
        Robustly extract text from Responses API output for SDK 2.9.0.

        We try:
          - response.output_text (if available)
          - response.output[..].content[..].text
          - fallback to str(response)
        """
        # Newer SDKs sometimes expose a convenience attribute
        if hasattr(response, "output_text"):
            try:
                return response.output_text
            except Exception:
                logger.exception("Failed to read response.output_text; falling back.")

        pieces: List[str] = []
        try:
            output_blocks = getattr(response, "output", []) or []
            for block in output_blocks:
                block_type = getattr(block, "type", None)
                contents = getattr(block, "content", []) or []
                for item in contents:
                    item_type = getattr(item, "type", None)
                    # For text-like blocks
                    if item_type in ("output_text", "text"):
                        text_val = getattr(item, "text", None)
                        if isinstance(text_val, str):
                            pieces.append(text_val)
        except Exception:
            logger.exception("Failed to parse response.output; using str(response).")
            return str(response)

        if pieces:
            return "\n".join(pieces)

        # Ultimate fallback
        return str(response)

    def _upload_pdf(self, document_id: str, pdf_path: Optional[Path]) -> Optional[str]:
        """
        Upload the PDF (if present) as user_data and return file_id.
        """
        if not pdf_path or not pdf_path.is_file():
            logger.info(
                "No PDF found for document_id=%s; continuing with JSON-only logic.",
                document_id,
            )
            return None

        try:
            with pdf_path.open("rb") as f:
                uploaded = self.client.files.create(
                    file=f,
                    # We want general file usage, not 'vision'
                    purpose="user_data",
                )
            pdf_file_id = uploaded.id
            logger.info(
                "Uploaded PDF for document_id=%s, file_id=%s, path=%s",
                document_id,
                pdf_file_id,
                pdf_path,
            )
            return pdf_file_id
        except Exception:
            logger.exception(
                "Failed to upload PDF for document_id=%s; continuing without PDF.",
                document_id,
            )
            return None

    # ------------------------- JSON PASS -------------------------

    def _build_llm_json_view(self, json_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a *semantic* JSON view for the LLM, much smaller than the full
        DWG→JSON, but preserving all the information we care about for
        summarization:

          - metadata (schema_version, header)
          - layer names + counts
          - entity type counts
          - all dimensions (type, text, value, units, layer, etc.)
          - all notes/text (text, layer, inferred note_type)

        The full raw JSON is still kept on disk / in the DB; this is only what
        we send to the model for summarization.
        """
        entities = json_dict.get("entities", []) or []

        entity_type_counts: Dict[str, int] = {}
        layer_counts: Dict[str, int] = {}

        dimensions: List[Dict[str, Any]] = []
        notes: List[Dict[str, Any]] = []

        for ent in entities:
            etype = (ent.get("type") or "").strip()
            etype_lower = etype.lower()
            layer = ent.get("layer")

            # entity type stats
            if etype:
                entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1

            # layer stats
            if layer:
                layer_counts[layer] = layer_counts.get(layer, 0) + 1

            # dimensions
            if "dim" in etype_lower:
                dimensions.append(
                    {
                        "index": ent.get("index"),
                        "type": etype,
                        "layer": layer,
                        "handle": ent.get("handle"),
                        "owner_handle": ent.get("owner_handle"),
                        "dim_text": ent.get("text"),
                        "dim_value": ent.get("value"),
                        "units": ent.get("units"),
                        # optional: keep light geometry; omit if too big
                        "geometry": ent.get("geometry"),
                    }
                )
                continue

            # notes / text (TEXT, MTEXT, etc.)
            if "text" in etype_lower:
                raw_text = ent.get("text") or ""
                note_type = self._infer_note_type_from_text(raw_text)
                notes.append(
                    {
                        "index": ent.get("index"),
                        "type": etype,
                        "layer": layer,
                        "handle": ent.get("handle"),
                        "note_type": note_type,
                        "text": raw_text,
                        # light geometry is optional
                        "geometry": ent.get("geometry"),
                    }
                )
                continue

        layers_list = [
            {"name": name, "entity_count": count}
            for name, count in sorted(layer_counts.items(), key=lambda kv: kv[0])
        ]

        llm_view = {
            "metadata": {
                "schema_version": json_dict.get("schema_version"),
                "dwg_header": json_dict.get("header"),
                "num_entities": len(entities),
            },
            "entity_type_counts": entity_type_counts,
            "layers": layers_list,
            "dimensions": dimensions,
            "notes": notes,
        }
        return llm_view

    def _infer_note_type_from_text(self, raw_text: str) -> str:
        """
        Lightweight inference of note type from raw text, similar to ETL infer.
        """
        t = (raw_text or "").lower()
        if any(tok in t for tok in ["±", "tolerance", "tol"]):
            return "tolerance"
        if any(tok in t for tok in ["⌀", "gd&t", "true position", "flatness"]):
            return "gdandt"
        return "general"


        # ------------------------- JSON PASS -------------------------

    def _summarize_json(self, document_id: str, json_dict: Dict[str, Any]) -> str:
        """
        Summarize the DWG→JSON structure using a *semantic* projection:

          1) Build a reduced JSON view focusing on:
             - metadata
             - entity type counts
             - layers
             - dimensions
             - notes

          2) Serialize compactly.

          3) If it fits under MAX_CHARS, summarize in a single call.

          4) Otherwise, chunk by characters and do a small number of calls,
             then combine chunk summaries.

        The full raw JSON is *not* truncated; it is still stored on disk/DB.
        Only the derived, semantic view is fed to the model.
        """
        llm_view = self._build_llm_json_view(json_dict)

        compact_json = json.dumps(llm_view, separators=(",", ":"))

        MAX_CHARS = 60000  # ~15k tokens; safe headroom for prompt + output

        if len(compact_json) <= MAX_CHARS:
            logger.info(
                "Semantic JSON view for document_id=%s fits in a single call (%d chars).",
                document_id,
                len(compact_json),
            )
            # Single-call summary
            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "You are CadSentinel. You are given a semantic JSON "
                                    "view of a mechanical drawing derived from DWG.\n\n"
                                    "The JSON includes:\n"
                                    "- metadata and DWG header (if available)\n"
                                    "- entity type counts\n"
                                    "- layers and how many entities they contain\n"
                                    "- a list of dimensions (text, value, units, layer)\n"
                                    "- a list of notes/text with inferred types.\n\n"
                                    "From this, produce a concise but thorough technical "
                                    "summary of the drawing:\n"
                                    "- part identity (name/number if present)\n"
                                    "- main geometric features (holes, slots, bosses, etc.)\n"
                                    "- critical dimensions and tolerances\n"
                                    "- GD&T callouts and datums\n"
                                    "- important notes, inspection/manufacturing hints.\n\n"
                                    "Return a technical narrative in text form."
                                ),
                            },
                            {
                                "type": "input_text",
                                "text": compact_json,
                            },
                        ],
                    }
                ],
            )
            return self._extract_text_from_response(response)

        # If we get here, even the semantic view is large; chunk it.
        CHUNK_SIZE = MAX_CHARS
        chunks: List[str] = [
            compact_json[i : i + CHUNK_SIZE]
            for i in range(0, len(compact_json), CHUNK_SIZE)
        ]

        logger.info(
            "Semantic JSON view for document_id=%s split into %d chunks "
            "(total %d chars).",
            document_id,
            len(chunks),
            len(compact_json),
        )

        chunk_summaries: List[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            chunk_summary = self._summarize_json_chunk(
                document_id=document_id,
                chunk_idx=idx,
                total_chunks=len(chunks),
                chunk_text=chunk,
            )
            chunk_summaries.append(chunk_summary)

        combined_input = "\n\n--- CHUNK SUMMARY SEPARATOR ---\n\n".join(
            chunk_summaries
        )

        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are CadSentinel. You are given multiple partial "
                                "summaries of a semantic JSON view of a mechanical drawing.\n\n"
                                "Each partial summary corresponds to a chunk of the JSON.\n"
                                "Merge them into a single coherent JSON-centric summary. "
                                "Focus on:\n"
                                "- part identity\n"
                                "- key features\n"
                                "- critical dimensions and tolerances\n"
                                "- GD&T\n"
                                "- important notes.\n\n"
                                "Return a technical narrative in text form."
                            ),
                        },
                        {
                            "type": "input_text",
                            "text": combined_input,
                        },
                    ],
                }
            ],
        )

        return self._extract_text_from_response(response)

    def _summarize_json_chunk(
        self,
        *,
        document_id: str,
        chunk_idx: int,
        total_chunks: int,
        chunk_text: str,
    ) -> str:
        """
        Summarize a single chunk of the *semantic* JSON view into a concise
        technical text summary.
        """
        logger.info(
            "Summarizing semantic JSON chunk %d/%d for document_id=%s.",
            chunk_idx,
            total_chunks,
            document_id,
        )

        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"You are CadSentinel. This is semantic JSON chunk "
                                f"{chunk_idx} of {total_chunks} for a mechanical drawing.\n\n"
                                "The JSON contains metadata, entity type counts, layers, "
                                "dimensions, and notes.\n\n"
                                "From this chunk only, extract and describe:\n"
                                "- relevant dimensions and what they apply to\n"
                                "- any tolerances or GD&T implied by notes\n"
                                "- anything notable about layers or feature types.\n\n"
                                "Return a concise technical summary in text form."
                            ),
                        },
                        {
                            "type": "input_text",
                            "text": chunk_text,
                        },
                    ],
                }
            ],
        )

        return self._extract_text_from_response(response)



    # ------------------------- PDF PASS -------------------------

    def _summarize_pdf(self, document_id: str, pdf_file_id: str) -> str:
        """
        Summarize the PDF rendering of the drawing:
          - views, layout, orientation
          - callout placement
          - GD&T frames and notes as they appear visually
        """
        logger.info(
            "Summarizing PDF for document_id=%s with file_id=%s.",
            document_id,
            pdf_file_id,
        )

        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are CadSentinel, analyzing a mechanical drawing PDF.\n"
                                "Describe the drawing from a visual/layout perspective:\n"
                                "- primary views (front, top, side, section views, details)\n"
                                "- arrangement and spacing of views\n"
                                "- locations of key dimensions and notes\n"
                                "- presence and placement of GD&T feature control frames\n"
                                "- title block information if legible.\n\n"
                                "Return a technical narrative in text form."
                            ),
                        },
                        {
                            "type": "input_file",
                            "file_id": pdf_file_id,
                        },
                    ],
                }
            ],
        )

        return self._extract_text_from_response(response)

    # ------------------------- FUSION PASS -------------------------

    def _fuse_summaries(
        self,
        *,
        document_id: str,
        json_summary: str,
        pdf_summary: str,
    ) -> Any:
        """
        Combine JSON-based summary and PDF-based summary into the final
        structured object expected by ETL.

        Expected output format:
        {
          "structured_summary": {...},
          "long_form_description": "...",
          "short_description": "..."
        }
        """
        logger.info(
            "Fusing JSON and PDF summaries for document_id=%s.", document_id
        )

        fusion_prompt = (
            "You are CadSentinel. You are given two summaries of the same "
            "mechanical drawing:\n"
            "1) JSON-based summary (symbolic, entity-level, from DWG→JSON)\n"
            "2) PDF-based summary (visual/layout-level, from PDF rendering)\n\n"
            "Integrate them into a single coherent description and structured "
            "summary for an engineering drawing retrieval system.\n\n"
            "Return a JSON object with fields:\n"
            "  structured_summary: a nested JSON object capturing:\n"
            "    - part identity (name, number if present)\n"
            "    - key geometric features (holes, slots, bosses, chamfers, threads)\n"
            "    - critical dimensions and tolerances\n"
            "    - GD&T callouts and datums\n"
            "    - manufacturing and inspection-relevant notes\n"
            "  long_form_description: a 2–6 paragraph technical narrative\n"
            "  short_description: a 1–2 sentence summary suitable for search results\n\n"
            "Be precise, technical, and concise. Return ONLY valid JSON."
        )

        combined_input = (
            "JSON-based summary:\n"
            f"{json_summary}\n\n"
            "PDF-based summary:\n"
            f"{pdf_summary}"
        )

        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": fusion_prompt},
                        {"type": "input_text", "text": combined_input},
                    ],
                }
            ],
        )

        text = self._extract_text_from_response(response)

        try:
            parsed = json.loads(text)
            return parsed
        except Exception:
            logger.exception(
                "Fusion output for document_id=%s was not valid JSON.", document_id
            )
            # Fall back to returning the raw text so ETL still has something
            return text

# ============================================================================
# OpenAI Embedding Provider
# ============================================================================

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    DEPRECATED: Ingestion and search now use app.services.embeddings.embed_texts()
    as the single embedding entrypoint.

    This class is kept only for backward compatibility or for potential reuse in
    specialized tools. Prefer embed_texts() for any new code paths.

    Historically, this used the OpenAI `text-embedding-3-small` model
    (1536-dimensional vectors) to match the `VECTOR(1536)` column in PostgreSQL.
    """

    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        self.model_name = model_name
        self.client = OpenAI()

    def _normalize_embedding(self, vec: List[float]) -> List[float]:
        """
        Ensure we always return exactly 1536 dimensions.

        Normally `text-embedding-3-small` already returns 1536-dim vectors,
        but we defensively truncate/pad in case the model is changed.
        """
        target_dim = 1536
        n = len(vec)
        if n == target_dim:
            return vec
        if n > target_dim:
            logger.warning(
                "Embedding length %d > %d; truncating.",
                n,
                target_dim,
            )
            return vec[:target_dim]
        # n < target_dim → pad with zeros
        logger.warning(
            "Embedding length %d < %d; padding with zeros.",
            n,
            target_dim,
        )
        return vec + [0.0] * (target_dim - n)

    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string.
        """
        if not text:
            # Avoid sending empty strings; just return a zero vector
            return [0.0] * 1536

        resp = self.client.embeddings.create(
            model=self.model_name,
            input=[text],
        )
        vec = resp.data[0].embedding
        return self._normalize_embedding(vec)

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """
        Batched embedding for multiple texts.
        """
        if not texts:
            return []

        # Filter out empty strings while preserving order and length
        sanitized = [t if t else " " for t in texts]

        resp = self.client.embeddings.create(
            model=self.model_name,
            input=sanitized,
        )

        vectors: List[List[float]] = []
        for record in resp.data:
            vectors.append(self._normalize_embedding(record.embedding))

        # Safety: resp.data length should equal len(texts)
        if len(vectors) != len(texts):
            logger.warning(
                "Embedding count mismatch: got %d vectors for %d texts.",
                len(vectors),
                len(texts),
            )

        return vectors


# ============================================================================
# Ollama Providers (Placeholders)
# ============================================================================

class OllamaSummaryProvider(SummaryProvider):
    """
    Placeholder for future on-prem summary model.
    """

    def __init__(self, model_name: str = "my-local-llm"):
        self.model_name = model_name

    def generate_summary(
        self,
        *,
        document_id: str,
        pdf_path: Optional[Path],
        json_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Ollama summary provider not implemented yet. "
            "Replace this stub with your local inference pipeline."
        )


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Placeholder for future on-prem embedding model.
    """

    def __init__(self, model_name: str = "my-local-embeddings"):
        self.model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError(
            "Ollama embedding provider not implemented yet. "
            "Replace this stub with your local embedding pipeline."
        )


# ============================================================================
# Provider Factory
# ============================================================================

def build_summary_provider(provider_name: str) -> SummaryProvider:
    if provider_name.lower() == "openai":
        return OpenAISummaryProvider()
    elif provider_name.lower() == "ollama":
        return OllamaSummaryProvider()
    else:
        raise ValueError(f"Unknown summary provider: {provider_name}")


def build_embedding_provider(provider_name: str) -> EmbeddingProvider:
    if provider_name.lower() == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_name.lower() == "ollama":
        return OllamaEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}")
