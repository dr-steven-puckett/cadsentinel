from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    Drawing,
    DrawingVersion,
    DrawingFile,
    Dimension,
    Note,
    DrawingSummary,
    Embedding,
)

from app.services.ai_providers import SummaryProvider
from app.services.embeddings import embed_texts, EMBEDDING_MODEL


logger = logging.getLogger(__name__)


# ======================================================================
# ETL RESULT OBJECT
# ======================================================================

class ETLResult:
    """
    Returned by run_drawing_etl().
    Used by the ingestion endpoint to add pipeline events.
    """
    def __init__(
        self,
        drawing_id: int,
        drawing_version_id: int,
        num_dimensions: int,
        num_notes: int,
        summary_id: Optional[int],
        num_embeddings: int,
    ) -> None:
        self.drawing_id = drawing_id
        self.drawing_version_id = drawing_version_id
        self.num_dimensions = num_dimensions
        self.num_notes = num_notes
        self.summary_id = summary_id
        self.num_embeddings = num_embeddings

    def dict(self) -> dict:
        return {
            "drawing_id": self.drawing_id,
            "drawing_version_id": self.drawing_version_id,
            "num_dimensions": self.num_dimensions,
            "num_notes": self.num_notes,
            "summary_id": self.summary_id,
            "num_embeddings": self.num_embeddings,
        }


# ======================================================================
# MAIN ETL FUNCTION
# ======================================================================

async def run_drawing_etl(
    *,
    db: Session,
    document_id: str,
    source_filename: str,
    json_path: Path,
    dwg_path: Path,
    dxf_path: Path,
    pdf_path: Optional[Path],
    png_path: Optional[Path],
    thumbnail_path: Optional[Path],
    summary_provider: SummaryProvider,
) -> ETLResult:

    """
    The core ETL for CadSentinel.

    Steps:
    1. Create/lookup Drawing
    2. Find or insert DrawingVersion (idempotent by dwg_sha256)
    3. Insert DrawingFiles
    4. Parse JSON → Dimensions + Notes
    5. Generate LLM summary (provider can be multi-pass JSON+PDF)
    6. Generate embeddings for summary, dimensions, notes
    7. Commit all changes
    """

    logger.info(f"Starting ETL for document_id={document_id}")

    # ------------------------------------------------------------------
    # 1. Ensure Drawing exists (one per document_id_sha)
    # ------------------------------------------------------------------
    drawing = (
        db.query(Drawing)
        .filter(Drawing.document_id_sha == document_id)
        .one_or_none()
    )

    if drawing is None:
        drawing = Drawing(document_id_sha=document_id)
        db.add(drawing)
        db.flush()  # get drawing.id

    # ------------------------------------------------------------------
    # 2. Find or create DrawingVersion for this dwg_sha256
    #    (dwg_sha256 is UNIQUE, so we must reuse if it already exists)
    # ------------------------------------------------------------------
    existing_version = (
        db.query(DrawingVersion)
        .filter(DrawingVersion.dwg_sha256 == document_id)
        .one_or_none()
    )

    if existing_version is not None:
        # Re-ingest: reuse the same version row and clean out old derived data
        version = existing_version
        logger.info(
            "Re-ingesting existing drawing_version_id=%s for dwg_sha256=%s; "
            "clearing previous extracted data",
            version.id,
            document_id,
        )

        # Keep it active and update filename
        version.is_active = True
        version.source_filename = source_filename

        # Delete previous derived rows so we don't duplicate things
        db.query(DrawingFile).filter(
            DrawingFile.drawing_version_id == version.id
        ).delete(synchronize_session=False)

        db.query(Dimension).filter(
            Dimension.drawing_version_id == version.id
        ).delete(synchronize_session=False)

        db.query(Note).filter(
            Note.drawing_version_id == version.id
        ).delete(synchronize_session=False)

        db.query(DrawingSummary).filter(
            DrawingSummary.drawing_version_id == version.id
        ).delete(synchronize_session=False)

        db.query(Embedding).filter(
            Embedding.drawing_version_id == version.id
        ).delete(synchronize_session=False)

        db.flush()

    else:
        # First time ingest for this DWG hash: create a new version
        # Deactivate previous versions (if any) for this drawing
        db.query(DrawingVersion).filter(
            DrawingVersion.drawing_id == drawing.id,
            DrawingVersion.is_active == True,
        ).update({DrawingVersion.is_active: False})

        version = DrawingVersion(
            drawing_id=drawing.id,
            revision_label=None,  # future support for Revision
            dwg_sha256=document_id,
            source_filename=source_filename,
            is_active=True,
        )
        db.add(version)
        db.flush()  # populate version.id

    # ------------------------------------------------------------------
    # 3. Register DrawingFiles
    # ------------------------------------------------------------------
    def _add_file(file_type: str, p: Optional[Path]):
        if p:
            try:
                db.add(
                    DrawingFile(
                        drawing_version_id=version.id,
                        file_type=file_type,
                        file_path=str(p),
                        file_size_bytes=p.stat().st_size,
                        mime_type=_guess_mime(file_type),
                    )
                )
            except Exception:
                logger.exception(f"Failed to register file {file_type}: {p}")

    _add_file("dwg", dwg_path)
    _add_file("dxf", dxf_path)
    _add_file("json", json_path)
    _add_file("pdf", pdf_path)
    _add_file("png_full", png_path)
    _add_file("png_thumb", thumbnail_path)

    # ------------------------------------------------------------------
    # 4. Parse JSON → Dimensions + Notes
    # ------------------------------------------------------------------
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    dims_inserted, notes_inserted = _extract_dimensions_and_notes(
        db=db,
        version_id=version.id,
        json_data=data,
    )

    # ------------------------------------------------------------------
    # 5. Generate LLM summary via provider
    # ------------------------------------------------------------------
    summary_output = summary_provider.generate_summary(
        document_id=document_id,
        pdf_path=pdf_path,
        json_dict=data,
    )

    structured = summary_output["structured_summary"]
    long_form = summary_output["long_form_description"]
    short = summary_output.get("short_description")

    summary_row = DrawingSummary(
        drawing_version_id=version.id,
        structured_summary=structured,
        long_form_description=long_form,
        short_description=short,
        model_name=summary_provider.model_name,
        prompt_version="1.0",
    )
    db.add(summary_row)
    db.flush()  # for summary_row.id

    # ------------------------------------------------------------------
    # 6. Generate embeddings
    # ------------------------------------------------------------------
    embeddings_created = await _generate_all_embeddings(
        db=db,
        version_id=version.id,
        summary_row=summary_row,
    )


    # ------------------------------------------------------------------
    # 7. Commit ETL
    # ------------------------------------------------------------------
    try:
        db.commit()
        logger.info(
            f"ETL completed: drawing_id={drawing.id}, version_id={version.id}, "
            f"{dims_inserted} dims, {notes_inserted} notes, {embeddings_created} embeddings"
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("ETL failed; DB rolled back")
        raise

    return ETLResult(
        drawing_id=drawing.id,
        drawing_version_id=version.id,
        num_dimensions=dims_inserted,
        num_notes=notes_inserted,
        summary_id=summary_row.id,
        num_embeddings=embeddings_created,
    )


# ======================================================================
# HELPERS
# ======================================================================

def _guess_mime(file_type: str) -> str:
    if file_type == "dwg":
        return "application/acad"
    if file_type == "dxf":
        return "application/dxf"
    if file_type == "pdf":
        return "application/pdf"
    if file_type.startswith("png"):
        return "image/png"
    if file_type == "json":
        return "application/json"
    return "application/octet-stream"


def _extract_dimensions_and_notes(
    *,
    db: Session,
    version_id: int,
    json_data: Dict[str, Any],
) -> tuple[int, int]:
    """
    Your C++ JSON exporter provides `entities[]` with types including:
      - TEXT → notes
      - DIMENSION → dimensions
      - MTEXT → notes
      - etc.

    We will generalize extraction here.
    """
    dims = 0
    notes = 0

    entities = json_data.get("entities", [])
    for ent in entities:
        ent_type = ent.get("type", "").lower()
        idx = ent.get("index")

        # --------------------------
        # DIMENSIONS
        # --------------------------
        if "dim" in ent_type:  # e.g., "DIMENSION_LINEAR"
            dim = Dimension(
                drawing_version_id=version_id,
                json_index=idx,
                dim_type=ent.get("type"),
                raw_type_code=ent.get("raw_type"),
                layer=ent.get("layer"),
                handle=ent.get("handle"),
                owner_handle=ent.get("owner_handle"),
                dim_text=ent.get("text"),
                dim_value=ent.get("value"),
                units=ent.get("units"),
                geometry=ent.get("geometry"),
            )
            db.add(dim)
            dims += 1

        # --------------------------
        # NOTES / TEXT
        # --------------------------
        elif "text" in ent_type:
            note = Note(
                drawing_version_id=version_id,
                json_index=idx,
                note_type=_infer_note_type(ent),
                text=ent.get("text", ""),
                layer=ent.get("layer"),
                handle=ent.get("handle"),
                geometry=ent.get("geometry"),
            )
            db.add(note)
            notes += 1

    return dims, notes


def _infer_note_type(ent: Dict[str, Any]) -> str:
    raw_text = (ent.get("text") or "").lower()
    if any(tok in raw_text for tok in ["±", "tolerance", "tol"]):
        return "tolerance"
    if any(tok in raw_text for tok in ["⌀", "gd&t", "true position", "flatness"]):
        return "gdandt"
    return "general"


async def _generate_all_embeddings(
    *,
    db: Session,
    version_id: int,
    summary_row: DrawingSummary,
) -> int:
    embeddings_created = 0

    # -----------------------------------------------------
    # 1. Build list of (source_type, source_ref_id, text)
    # -----------------------------------------------------
    content_pieces: List[tuple[str, int, str]] = []

    # Summary long-form + short
    if summary_row.long_form_description:
        content_pieces.append(
            ("summary", summary_row.id, summary_row.long_form_description)
        )
    if summary_row.short_description:
        content_pieces.append(
            ("summary_short", summary_row.id, summary_row.short_description)
        )

    # Dimensions
    dim_rows = (
        db.query(Dimension)
        .filter(Dimension.drawing_version_id == version_id)
        .all()
    )
    for dim in dim_rows:
        text_parts: List[str] = []
        if dim.dim_text:
            text_parts.append(str(dim.dim_text))
        if dim.dim_value is not None:
            text_parts.append(f"= {dim.dim_value}")
        if dim.units:
            text_parts.append(f" {dim.units}")
        text = "".join(text_parts).strip()

        if text:
            content_pieces.append(("dimension", dim.id, text))

    # Notes
    note_rows = (
        db.query(Note)
        .filter(Note.drawing_version_id == version_id)
        .all()
    )
    for note in note_rows:
        if note.text and note.text.strip():
            content_pieces.append(("note", note.id, note.text.strip()))

    if not content_pieces:
        return 0

    # -----------------------------------------------------
    # 2. Batch embed via shared embed_texts()
    # -----------------------------------------------------
    texts = [t for (_, _, t) in content_pieces]
    vectors = await embed_texts(texts)

    if len(vectors) != len(content_pieces):
        logger.warning(
            "Embedding provider returned %d vectors for %d texts; "
            "skipping embeddings for this drawing_version_id=%s",
            len(vectors),
            len(content_pieces),
            version_id,
        )
        return 0

    # -----------------------------------------------------
    # 3. Insert Embedding rows
    # -----------------------------------------------------
    for (source_type, ref_id, text), vec in zip(content_pieces, vectors):
        row = Embedding(
            drawing_version_id=version_id,
            source_type=source_type,
            source_ref_id=ref_id,
            content=text,
            embedding=vec,
            model_name=EMBEDDING_MODEL,  # from app.services.embeddings
        )
        db.add(row)
        embeddings_created += 1

    return embeddings_created
