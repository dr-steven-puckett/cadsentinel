from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI  # pip install openai

from app.api.schemas import DrawingStructuredSummary
from app.config import get_settings  # ⬅ import your settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client once (expects OPENAI_API_KEY in env)
_client: OpenAI | None = None
_settings = get_settings()

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = _settings.OPENAI_API_KEY
        if not api_key:
            # This gives you a clear error if the key isn't configured
            raise RuntimeError(
                "OPENAI_API_KEY is not set in settings. "
                "Make sure it is defined in your .env or environment."
            )
        _client = OpenAI(api_key=api_key)
    return _client


SYSTEM_PROMPT = """
You are an expert in mechanical engineering drawings, CAD standards, GD&T, and manufacturing.

Your job is to analyze a single technical drawing using BOTH:
1) a DWG/DXF-derived JSON description of entities and metadata, and
2) the human-intended content of the drawing (title block, notes, annotations, etc.).

You must:
- Be precise and conservative: DO NOT hallucinate dimensions, tolerances, materials, or standards that are not present.
- Prefer direct evidence from the JSON over assumptions.
- Explain what is clearly specified vs what is implied or missing.
- Use clear, engineering-oriented language.
- When in doubt, explicitly say that information is not given.

Return ONLY a single JSON object with the following schema:

{
  "structured_summary": {
    "drawing_id": "string",
    "title_block": {
      "part_name": "string or null",
      "drawing_number": "string or null",
      "revision": "string or null",
      "scale": "string or null",
      "units": "string or null",
      "projection": "string or null",
      "material": "string or null",
      "standard_references": ["string"]
    },
    "part_type": "single_part | assembly | weldment | sheet_metal | other | null",
    "overall_description": "string or null",
    "key_features": ["string"],
    "critical_dimensions": ["string"],
    "gdandt_summary": ["string"],
    "manufacturing_notes": ["string"],
    "known_gaps_or_ambiguities": ["string"]
  },
  "long_form_description": "string"
}

No extra text, comments, or Markdown.
"""


def build_user_prompt(document_id: str, json_text: str, pdf_path: Path) -> str:
    """
    For now we primarily use the JSON content as the text input.
    The PDF path is included in the prompt so the model 'knows'
    this is a drawing; in a later revision you can wire the PDF
    as a true vision/file input to a multimodal model.
    """
    return f"""
You are analyzing a single engineering drawing.

Drawing ID: {document_id}
The drawing has been exported to PDF at: {pdf_path}

Below is the DWG/DXF-derived JSON representation of the drawing
entities and metadata. Use it as your primary source of truth.

================ JSON DWG/DXF DATA ================
{json_text}
===================================================

Using this information, produce the JSON object described in the system prompt.
"""


def summarize_drawing_with_llm(
    document_id: str,
    json_path: Path,
    pdf_path: Path,
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Call an LLM to generate a structured summary + long-form description.

    Returns a dict with keys:
      - "structured_summary"
      - "long_form_description"
      - "raw_model_output"
    """
    if not json_path.is_file():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    json_text = json_path.read_text(encoding="utf-8")

    system_prompt = SYSTEM_PROMPT.strip()
    user_prompt = build_user_prompt(document_id, json_text, pdf_path)

    logger.info(
        "Calling LLM summarizer for document_id=%s, json=%s, pdf=%s",
        document_id,
        json_path,
        pdf_path,
    )

    client = get_openai_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = resp.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM returned empty content")

    raw_text = content.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM response as JSON: %s\n%s", exc, raw_text)
        raise

    # Attach raw_model_output for debugging
    parsed["raw_model_output"] = raw_text
    return parsed


def parse_structured_summary(data: Dict[str, Any]) -> DrawingStructuredSummary:
    """
    Convert the dict from the LLM into a DrawingStructuredSummary model.
    """
    return DrawingStructuredSummary(**data["structured_summary"])
