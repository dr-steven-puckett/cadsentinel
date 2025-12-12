import logging
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# You can configure this in settings
ARTIFACT_ROOT = Path("/mnt/cadsentinel/artifacts")


def get_artifact_path(drawing_version_id: str, kind: str) -> Path:
    """
    Map kind + drawing_version_id to a file path.
    Adapt this to your actual directory layout.
    """
    logger.debug("Resolving artifact path for %s kind=%s", drawing_version_id, kind)
    # Example layout: /root/{drawing_version_id}/thumbnail.png etc.
    kind_to_name = {
        "thumbnail": "thumbnail.png",
        "png": "drawing.png",
        "pdf": "drawing.pdf",
        "json": "dwg.json",
    }
    filename = kind_to_name.get(kind)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown artifact kind {kind}")
    return ARTIFACT_ROOT / drawing_version_id / filename
