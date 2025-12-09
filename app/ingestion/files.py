# app/ingestion/files.py

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.hashing import compute_document_id

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    document_id: str
    ingested_path: Path
    original_filename: str


def _ensure_dwg_extension(path: Path) -> None:
    """
    Optionally enforce that the file has a .dwg extension.

    For now we only log a warning if it's not .dwg, since some
    inputs may be oddly named. You can tighten this later if desired.
    """
    if path.suffix.lower() != ".dwg":
        logger.warning(
            "File does not have .dwg extension: %s (suffix=%s)",
            path,
            path.suffix,
        )


def ingest_dwg_file(src_path: Path, ingested_dir: Path) -> IngestionResult:
    """
    Compute document_id, copy the DWG to ingested_dir/<document_id>.dwg,
    and return metadata.

    Steps:
    - Validate source file exists.
    - Compute SHA256-based document_id.
    - Ensure ingested_dir exists.
    - Copy src_path → ingested_dir / f"{document_id}.dwg".
    - Return IngestionResult.
    """
    if not src_path.is_file():
        raise FileNotFoundError(f"Source DWG does not exist: {src_path}")

    _ensure_dwg_extension(src_path)

    document_id = compute_document_id(src_path)
    original_filename = src_path.name

    ingested_dir.mkdir(parents=True, exist_ok=True)
    dest_path = ingested_dir / f"{document_id}.dwg"

    # If the file already exists (same content, same hash),
    # we treat this as idempotent ingestion.
    if dest_path.exists():
        logger.info(
            "Ingested DWG already exists for document_id=%s at %s; "
            "skipping copy and returning existing path.",
            document_id,
            dest_path,
        )
    else:
        logger.info(
            "Copying DWG to ingested store: %s → %s",
            src_path,
            dest_path,
        )
        shutil.copy2(src_path, dest_path)

    return IngestionResult(
        document_id=document_id,
        ingested_path=dest_path,
        original_filename=original_filename,
    )

