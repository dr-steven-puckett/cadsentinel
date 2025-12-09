from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DwgToDxfError(RuntimeError):
    """Raised when dwg2dxf fails to convert a DWG file."""


def _extract_document_id_from_path(ingested_dwg_path: Path) -> str:
    return ingested_dwg_path.stem


def convert_dwg_to_dxf(
    ingested_dwg_path: Path,
    derived_dir: Path,
    dwg2dxf_path: str,
) -> Path:
    """
    Run dwg2dxf to convert the DWG file to DXF, returning the DXF path.

    Mirrors the working CLI invocation:

        dwg2dxf -v3 -y <input.dwg> -o <output.dxf>

    Uses derived_dir as cwd and <document_id>.dxf as output filename.
    """
    if not ingested_dwg_path.is_file():
        raise FileNotFoundError(f"Ingested DWG does not exist: {ingested_dwg_path}")

    derived_dir.mkdir(parents=True, exist_ok=True)

    document_id = _extract_document_id_from_path(ingested_dwg_path)
    dxf_filename = f"{document_id}.dxf"
    dxf_path = derived_dir / dxf_filename

    if dxf_path.exists():
        logger.info("Existing DXF found; removing before re-creating: %s", dxf_path)
        try:
            dxf_path.unlink()
        except Exception as exc:
            logger.exception("Failed to remove existing DXF file: %s", dxf_path)
            raise DwgToDxfError(
                f"Failed to remove existing DXF file before conversion: {dxf_path}"
            ) from exc

    logger.info(
        "Converting DWG to DXF via dwg2dxf: exe=%s, input=%s, output_dir=%s, output_name=%s",
        dwg2dxf_path,
        ingested_dwg_path,
        derived_dir,
        dxf_filename,
    )

    cmd = [
        dwg2dxf_path,
        "-v3",
        "-y",
        str(ingested_dwg_path),
        "-o",
        dxf_filename,  # name only; cwd = derived_dir
    ]

    # Capture as bytes to avoid UnicodeDecodeError, then decode with errors="replace"
    result = subprocess.run(
        cmd,
        cwd=derived_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = (result.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()

    dxf_exists = dxf_path.is_file()
    dxf_size = dxf_path.stat().st_size if dxf_exists else 0

    if result.returncode != 0:
        if dxf_exists and dxf_size > 0:
            logger.warning(
                "dwg2dxf exited with code %s for %s, but DXF file exists (%d bytes). "
                "Proceeding with DXF; stderr:\n%s",
                result.returncode,
                ingested_dwg_path,
                dxf_size,
                stderr,
            )
            logger.debug("dwg2dxf stdout:\n%s", stdout)
        else:
            logger.error(
                "dwg2dxf failed for %s (code=%s). No DXF produced.\nStderr:\n%s",
                ingested_dwg_path,
                result.returncode,
                stderr,
            )
            raise DwgToDxfError(
                f"dwg2dxf failed for {ingested_dwg_path} with code {result.returncode}; "
                f"no DXF produced. Stderr: {stderr}"
            )
    else:
        if not dxf_exists or dxf_size == 0:
            logger.error(
                "dwg2dxf reported success but DXF file is missing or empty: %s",
                dxf_path,
            )
            raise DwgToDxfError(
                f"dwg2dxf did not produce a valid DXF file: {dxf_path}"
            )

    logger.info("DWG→DXF conversion complete: %s (%d bytes)", dxf_path, dxf_size)
    return dxf_path

