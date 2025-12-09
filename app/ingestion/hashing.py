# app/ingestion/hashing.py

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1 MB per read


def _hash_stream(stream: BinaryIO) -> str:
    """
    Compute SHA256 hex digest from a binary stream, reading in chunks.

    The returned string is lowercase hex and is used as the canonical
    document_id for DWG files in CadSentinel.
    """
    sha = hashlib.sha256()
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        sha.update(chunk)
    return sha.hexdigest()


def compute_document_id(dwg_path: Path) -> str:
    """
    Read the DWG file in binary mode and return a SHA256 hex string.

    This must be stable and deterministic, as it is used as the
    canonical document_id throughout the system.
    """
    if not dwg_path.is_file():
        raise FileNotFoundError(f"DWG file does not exist: {dwg_path}")

    logger.info("Computing SHA256 document_id for DWG: %s", dwg_path)

    with dwg_path.open("rb") as f:
        digest = _hash_stream(f)

    logger.info("Computed document_id=%s for DWG=%s", digest, dwg_path)
    return digest

