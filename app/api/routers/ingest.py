# app/api/routers/ingest.py
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings, Settings
from app.db.session import get_db
from app.ingestion.dwg_to_dxf import convert_dwg_to_dxf, DwgToDxfError
from app.ingestion.dxf_render import (
    render_dxf_to_pdf,
    render_dxf_to_png,
    generate_thumbnail_from_png,
)
from app.ingestion.dwg_json import run_dwg_to_json
from app.ingestion.files import ingest_dwg_file
from app.api.schemas import (
    IngestArtifacts,
    IngestResponse,
    PipelineEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _event(
    step: str,
    message: str,
    level: str = "info",
) -> PipelineEvent:
    """Helper to create a PipelineEvent."""
    return PipelineEvent(
        timestamp=datetime.utcnow(),
        level=level,  # type: ignore[arg-type]
        step=step,
        message=message,
    )


@router.post(
    "/dwg",
    response_model=IngestResponse,
    summary="Ingest a DWG file and run the CadSentinel pipeline.",
)
async def ingest_dwg_endpoint(
    file: UploadFile = File(..., description="DWG file to ingest."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """
    End-to-end ingestion of a DWG file.

    - Computes SHA256 document_id
    - Copies file into ingested/<document_id>.dwg
    - Converts DWG → DXF via dwg2dxf
    - Renders DXF → PDF/PNG/thumbnail
    - Runs dwg_to_json
    - (Later) Indexes JSON into Postgres + pgvector

    Returns a rich response object with:
    - success flag
    - overall message
    - pipeline events (for UI log)
    - artifact paths
    """
    events: List[PipelineEvent] = []
    document_id: Optional[str] = None

    try:
        # 1) Save uploaded file to a temporary path
        events.append(_event("upload", f"Received file: {file.filename!r}"))
        temp_dir = Path(settings.ingested_dir) / "_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename

        with temp_path.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        events.append(_event("upload", f"Saved upload to temporary path: {temp_path}"))

        # 2) Ingest DWG → compute SHA and move into ingested/<doc_id>.dwg
        from app.ingestion.hashing import compute_document_id  # lazy import to avoid cycles

        document_id = compute_document_id(temp_path)
        events.append(_event("hash", f"Computed document_id (SHA256): {document_id}"))

        # Use our ingest_dwg_file helper to copy into the canonical ingested folder
        from app.ingestion.files import ingest_dwg_file

        ingestion_result = ingest_dwg_file(
            src_path=temp_path,
            ingested_dir=Path(settings.ingested_dir),
        )
        events.append(
            _event(
                "ingest",
                f"Ingested DWG as {ingestion_result.ingested_path}",
            )
        )

        ingested_dwg = ingestion_result.ingested_path
        derived_dir = Path(settings.derived_dir)
        derived_dir.mkdir(parents=True, exist_ok=True)

        # 3) DWG → DXF via dwg2dxf
        try:
            events.append(
                _event(
                    "dwg_to_dxf",
                    f"Running dwg2dxf for {ingested_dwg} using {settings.dwg2dxf_path}",
                )
            )
            dxf_path = convert_dwg_to_dxf(
                ingested_dwg_path=ingested_dwg,
                derived_dir=derived_dir,
                dwg2dxf_path=settings.dwg2dxf_path,
            )
            events.append(
                _event(
                    "dwg_to_dxf",
                    f"DXF created: {dxf_path}",
                )
            )
        except DwgToDxfError as exc:
            # DXF rendering is important for UI, but JSON/embeddings could still proceed later.
            logger.exception("DWG→DXF conversion failed for %s", ingested_dwg)
            events.append(
                _event(
                    "dwg_to_dxf",
                    f"DXF conversion failed: {exc}",
                    level="error",
                )
            )
            # For now, treat as fatal. Later we can downgrade this to a warning and continue.
            return IngestResponse(
                success=False,
                document_id=document_id,
                message="DWG ingestion failed during DWG→DXF conversion.",
                events=events,
                artifacts=IngestArtifacts(
                    dwg_path=str(ingested_dwg),
                ),
            )

        # 4) DXF → PDF/PNG/thumbnail
        pdf_path = derived_dir / f"{document_id}.pdf"
        png_path = derived_dir / f"{document_id}.png"
        thumb_path = derived_dir / f"{document_id}_thumbnail.png"

        try:
            events.append(
                _event(
                    "render_pdf",
                    f"Rendering PDF: {pdf_path}",
                )
            )
            render_dxf_to_pdf(dxf_path, pdf_path, dpi=300)
            events.append(
                _event(
                    "render_pdf",
                    f"PDF rendered: {pdf_path}",
                )
            )
        except Exception as exc:
            logger.exception("DXF→PDF rendering failed for %s", dxf_path)
            events.append(
                _event(
                    "render_pdf",
                    f"Failed to render PDF: {exc}",
                    level="warning",
                )
            )
            pdf_path = None

        try:
            events.append(
                _event(
                    "render_png",
                    f"Rendering PNG: {png_path}",
                )
            )
            render_dxf_to_png(dxf_path, png_path, dpi=300)
            events.append(
                _event(
                    "render_png",
                    f"PNG rendered: {png_path}",
                )
            )

            events.append(
                _event(
                    "render_thumbnail",
                    f"Rendering thumbnail: {thumb_path}",
                )
            )
            generate_thumbnail_from_png(png_path, thumb_path, max_size=512)
            events.append(
                _event(
                    "render_thumbnail",
                    f"Thumbnail rendered: {thumb_path}",
                )
            )
        except Exception as exc:
            logger.exception("DXF→PNG/thumbnail rendering failed for %s", dxf_path)
            events.append(
                _event(
                    "render_png",
                    f"Failed to render PNG/thumbnail: {exc}",
                    level="warning",
                )
            )
            png_path = None
            thumb_path = None

        # 5) DWG → JSON (C++ dwg_to_json)
        try:
            events.append(
                _event(
                    "dwg_to_json",
                    f"Running dwg_to_json for {ingested_dwg}",
                )
            )
            json_path = run_dwg_to_json(
                ingested_dwg_path=ingested_dwg,
                derived_dir=derived_dir,
                dwg_to_json_path=settings.dwg2json_path,
            )
            events.append(
                _event(
                    "dwg_to_json",
                    f"JSON created: {json_path}",
                )
            )
        except Exception as exc:
            logger.exception("DWG→JSON conversion failed for %s", ingested_dwg)
            events.append(
                _event(
                    "dwg_to_json",
                    f"Failed to generate JSON: {exc}",
                    level="error",
                )
            )
            return IngestResponse(
                success=False,
                document_id=document_id,
                message="DWG ingestion failed during DWG→JSON conversion.",
                events=events,
                artifacts=IngestArtifacts(
                    dwg_path=str(ingested_dwg),
                    dxf_path=str(dxf_path),
                    pdf_path=str(pdf_path) if pdf_path else None,
                    png_path=str(png_path) if png_path else None,
                    thumbnail_path=str(thumb_path) if thumb_path else None,
                ),
            )

        # TODO: Phase 7/8 – call index_drawing(...) and append events for embeddings, DB, etc.

        events.append(
            _event(
                "complete",
                "DWG ingestion pipeline completed successfully.",
            )
        )

        return IngestResponse(
            success=True,
            document_id=document_id,
            message="DWG ingested and processed successfully.",
            events=events,
            artifacts=IngestArtifacts(
                dwg_path=str(ingested_dwg),
                dxf_path=str(dxf_path),
                pdf_path=str(pdf_path) if pdf_path else None,
                png_path=str(png_path) if png_path else None,
                thumbnail_path=str(thumb_path) if thumb_path else None,
                json_path=str(json_path),
            ),
        )

    except Exception as exc:
        logger.exception("Unhandled error during DWG ingestion.")
        # If we got an exception before computing document_id, it may be None
        events.append(
            _event(
                "unhandled_error",
                f"Unhandled error: {exc}",
                level="error",
            )
        )
        return IngestResponse(
            success=False,
            document_id=document_id,
            message="DWG ingestion failed due to an internal error.",
            events=events,
            artifacts=None,
        )

