# app/ingestion/dwg_json.py
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DwgToJsonError(RuntimeError):
    """Raised when dwg_to_json fails to produce valid JSON."""


def _extract_document_id_from_path(ingested_dwg_path: Path) -> str:
    # DWG files are named <document_id>.dwg in the ingested directory
    return ingested_dwg_path.stem


def run_dwg_to_json(
    ingested_dwg_path: Path,
    derived_dir: Path,
    dwg_to_json_path: str,
) -> Path:
    """
    Call the C++ dwg_to_json tool and save its JSON output to
    derived/<document_id>.json.

    Assumes dwg_to_json emits valid CadSentinel DWG JSON to stdout.
    """
    if not ingested_dwg_path.is_file():
        raise FileNotFoundError(f"Ingested DWG does not exist: { ingested_dwg_path }")

    derived_dir.mkdir(parents=True, exist_ok=True)

    document_id = _extract_document_id_from_path(ingested_dwg_path)
    json_path = derived_dir / f"{document_id}.json"

    # Resolve dwg_to_json_path: it may be absolute, relative, or just a name on PATH
    exe = Path(dwg_to_json_path)

    if exe.is_dir():
        # Catch exactly the situation you're seeing now
        raise DwgToJsonError(
            f"dwg_to_json_path points to a directory, not an executable: {exe}"
        )

    if not exe.is_file():
        # Try PATH lookup if only a name is provided
        resolved = shutil.which(dwg_to_json_path)
        if resolved is None:
            raise DwgToJsonError(
                f"dwg_to_json executable not found: {dwg_to_json_path!r}. "
                f"Provide a full path in DWG2JSON_PATH or ensure it's on PATH."
            )
        exe = Path(resolved)

    logger.info(
        "Running dwg_to_json: exe=%s, input=%s, output=%s",
        exe,
        ingested_dwg_path,
        json_path,
    )

    cmd = [
        str(exe),
        str(ingested_dwg_path),
    ]

    result = subprocess.run(
        cmd,
        cwd=derived_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")

    if result.returncode != 0:
        logger.error(
            "dwg_to_json failed for %s (code=%s). Stderr:\n%s",
            ingested_dwg_path,
            result.returncode,
            stderr,
        )
        raise DwgToJsonError(
            f"dwg_to_json failed for {ingested_dwg_path} with code {result.returncode}. "
            f"Stderr: {stderr}"
        )

    # Validate JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON emitted by dwg_to_json: %s", exc)
        raise DwgToJsonError(f"dwg_to_json emitted invalid JSON: {exc}") from exc

    # Optional: sanity checks on expected keys
    required_keys = ["file", "schema_version", "header", "layers", "entities"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        logger.warning(
            "dwg_to_json output is missing expected keys %s for %s",
            missing,
            ingested_dwg_path,
        )

    # Write to disk
    json_text = json.dumps(data, indent=2)
    json_path.write_text(json_text, encoding="utf-8")

    logger.info(
        "DWG→JSON completed: %s (%.1f KB)",
        json_path,
        json_path.stat().st_size / 1024.0,
    )

    return json_path

