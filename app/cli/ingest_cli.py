# app/cli/ingest_cli.py

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.config import get_settings
from app.ingestion.files import ingest_dwg_file
from app.logging_config import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CadSentinel DWG ingestion CLI: compute document_id and copy to ingested/."
    )
    parser.add_argument(
        "dwg_path",
        type=str,
        help="Path to the source DWG file.",
    )
    parser.add_argument(
        "--ingested-dir",
        type=str,
        default=None,
        help="Optional override for the ingested directory. "
             "Defaults to INGESTED_DIR from settings.",
    )

    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    dwg_path = Path(args.dwg_path).expanduser().resolve()
    ingested_dir = (
        Path(args.ingested_dir).expanduser().resolve()
        if args.ingested_dir
        else Path(settings.ingested_dir).expanduser().resolve()
    )

    logger.info("Starting DWG ingestion")
    logger.info("Source DWG: %s", dwg_path)
    logger.info("Ingested dir: %s", ingested_dir)

    result = ingest_dwg_file(dwg_path, ingested_dir)

    print("Ingestion complete:")
    print(f"  document_id:   {result.document_id}")
    print(f"  ingested_path: {result.ingested_path}")
    print(f"  original_name: {result.original_filename}")


if __name__ == "__main__":
    main()

