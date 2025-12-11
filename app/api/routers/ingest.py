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
from app.ingestion.hashing import compute_document_id

from app.services.etl_dwg import run_drawing_etl
from app.services.ai_providers import (
    build_summary_provider,
)

from app.api.schemas import (
    IngestArtifacts,
    IngestResponse,
    PipelineEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _event(step: str, message: str, level: str = "info") -> PipelineEvent:
    return PipelineEvent(
        timestamp=datetime.utcnow(),
        level=level,
        step=step,
        message=message,
    )


@router.post(
    "/dwg",
    response_model=IngestResponse,
    summary="Ingest a DWG file, extract geometry, generate summary & embeddings.",
)
async def ingest_dwg_endpoint(
    file: UploadFile = File(..., description="DWG file to ingest."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:

    events: List[PipelineEvent] = []
    document_id: Optional[str] = None

    try:
        # ======================================================================
        # 1. Save uploaded DWG → temp file
        # ======================================================================
        events.append(_event("upload", f"Received file: {file.filename!r}"))

        temp_dir = Path(settings.ingested_dir) / "_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / file.filename

        with temp_path.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        events.append(
            _event("upload", f"Saved temporary upload to {temp_path}")
        )

        # ======================================================================
        # 2. Compute document_id + ingest_ dwg_file
        # ======================================================================
        document_id = compute_document_id(temp_path)
        events.append(
            _event("hash", f"Computed document_id (SHA256): {document_id}")
        )

        ingestion_result = ingest_dwg_file(
            src_path=temp_path,
            ingested_dir=Path(settings.ingested_dir),
        )
        ingested_dwg = ingestion_result.ingested_path

        events.append(
            _event("ingest", f"Ingested DWG to {ingested_dwg}")
        )

        derived_dir = Path(settings.derived_dir)
        derived_dir.mkdir(parents=True, exist_ok=True)

        # ======================================================================
        # 3. DWG → DXF
        # ======================================================================
        try:
            events.append(
                _event("dwg_to_dxf", f"Running dwg2dxf using {settings.dwg2dxf_path}")
            )

            dxf_path = convert_dwg_to_dxf(
                ingested_dwg_path=ingested_dwg,
                derived_dir=derived_dir,
                dwg2dxf_path=settings.dwg2dxf_path,
            )

            events.append(
                _event("dwg_to_dxf", f"DXF created: {dxf_path}")
            )

        except DwgToDxfError as exc:
            logger.exception("DWG→DXF failed")
            events.append(
                _event("dwg_to_dxf", f"DXF conversion failed: {exc}", "error")
            )

            return IngestResponse(
                success=False,
                document_id=document_id,
                message="DWG ingestion failed during DWG→DXF.",
                events=events,
                artifacts=IngestArtifacts(dwg_path=str(ingested_dwg)),
            )

        # ======================================================================
        # 4. DXF → PDF / PNG / thumbnail
        # ======================================================================
        pdf_path = derived_dir / f"{document_id}.pdf"
        png_path = derived_dir / f"{document_id}.png"
        thumb_path = derived_dir / f"{document_id}_thumbnail.png"

        # ---- PDF ----
        try:
            events.append(_event("render_pdf", f"Rendering PDF: {pdf_path}"))
            render_dxf_to_pdf(dxf_path, pdf_path, dpi=300)
            events.append(_event("render_pdf", f"PDF rendered: {pdf_path}"))
        except Exception as exc:
            logger.exception("PDF render failed")
            events.append(
                _event("render_pdf", f"PDF render failed: {exc}", "warning")
            )
            pdf_path = None

        # ---- PNG + thumbnail ----
        try:
            events.append(_event("render_png", f"Rendering PNG: {png_path}"))
            render_dxf_to_png(dxf_path, png_path, dpi=300)
            events.append(_event("render_png", f"PNG rendered: {png_path}"))

            events.append(_event("render_thumbnail", f"Rendering thumbnail: {thumb_path}"))
            generate_thumbnail_from_png(png_path, thumb_path, max_size=512)
            events.append(_event("render_thumbnail", f"Thumbnail rendered: {thumb_path}"))
        except Exception as exc:
            logger.exception("PNG/thumb render failed")
            events.append(
                _event("render_png", f"PNG/thumbnail render failed: {exc}", "warning")
            )
            png_path = None
            thumb_path = None

        # ======================================================================
        # 5. DWG → JSON (C++ extractor)
        # ======================================================================
        try:
            events.append(_event("dwg_to_json", "Running dwg_to_json extractor..."))

            json_path = run_dwg_to_json(
                ingested_dwg_path=ingested_dwg,
                derived_dir=derived_dir,
                dwg_to_json_path=settings.dwg2json_path,
            )

            events.append(_event("dwg_to_json", f"JSON created: {json_path}"))

        except Exception as exc:
            logger.exception("DWG→JSON failed")
            events.append(
                _event("dwg_to_json", f"JSON conversion failed: {exc}", "error")
            )
            return IngestResponse(
                success=False,
                document_id=document_id,
                message="DWG ingestion failed during DWG→JSON.",
                events=events,
                artifacts=IngestArtifacts(
                    dwg_path=str(ingested_dwg),
                    dxf_path=str(dxf_path),
                    pdf_path=str(pdf_path) if pdf_path else None,
                    png_path=str(png_path) if png_path else None,
                    thumbnail_path=str(thumb_path) if thumb_path else None,
                ),
            )

        # ======================================================================
        # 6. ETL (DB insertions, summary, embeddings)
        # ======================================================================
        # 6. ETL (DB insertions, summary, embeddings)
        events.append(_event("etl", "Starting ETL processing..."))
        provider_name = getattr(settings, "ai_provider", "openai")

        summary_provider = build_summary_provider(provider_name)

        try:
            etl_result = await run_drawing_etl(
                db=db,
                document_id=document_id,
                source_filename=file.filename,
                json_path=json_path,
                dwg_path=ingested_dwg,
                dxf_path=dxf_path,
                pdf_path=pdf_path,
                png_path=png_path,
                thumbnail_path=thumb_path,
                summary_provider=summary_provider,
            )
            
            events.append(
                _event(
                    "etl",
                    f"ETL complete: {etl_result.num_dimensions} dims, "
                    f"{etl_result.num_notes} notes, {etl_result.num_embeddings} embeddings",
                )
            )

        except Exception as exc:
            logger.exception("ETL failed")
            db.rollback()
            events.append(
                _event("etl", f"ETL failed: {exc}", "error")
            )
            return IngestResponse(
                success=False,
                document_id=document_id,
                message="ETL failed.",
                events=events,
                artifacts=IngestArtifacts(
                    dwg_path=str(ingested_dwg),
                    dxf_path=str(dxf_path),
                    json_path=str(json_path),
                ),
            )

        # ======================================================================
        # 7. Complete pipeline
        # ======================================================================
        events.append(_event("complete", "DWG ingestion + ETL completed successfully."))

        return IngestResponse(
            success=True,
            document_id=document_id,
            message="DWG fully processed, summarized, and embedded.",
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

    # ======================================================================
    # 8. Unhandled exceptions
    # ======================================================================
    except Exception as exc:
        logger.exception("Unhandled error during DWG ingestion.")
        events.append(
            _event("unhandled_error", f"Unhandled error: {exc}", "error")
        )
        return IngestResponse(
            success=False,
            document_id=document_id,
            message="Ingestion failed due to internal error.",
            events=events,
            artifacts=None,
        )
