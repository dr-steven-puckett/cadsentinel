import logging
from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import HTTPException

from app.services import artifact_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _serve_artifact(drawing_version_id: str, kind: str, media_type: str) -> FileResponse:
    path = artifact_service.get_artifact_path(drawing_version_id, kind)
    if not path.exists():
        logger.warning("Artifact not found: %s", path)
        raise HTTPException(status_code=404, detail="Artifact not found")
    logger.debug("Serving artifact %s (%s)", path, media_type)
    return FileResponse(path, media_type=media_type)


@router.get("/{drawing_version_id}/thumbnail", summary="Thumbnail image")
def get_thumbnail(drawing_version_id: str):
    return _serve_artifact(drawing_version_id, "thumbnail", media_type="image/png")


@router.get("/{drawing_version_id}/png", summary="Full resolution PNG")
def get_png(drawing_version_id: str):
    return _serve_artifact(drawing_version_id, "png", media_type="image/png")


@router.get("/{drawing_version_id}/pdf", summary="Drawing PDF")
def get_pdf(drawing_version_id: str):
    return _serve_artifact(drawing_version_id, "pdf", media_type="application/pdf")


@router.get("/{drawing_version_id}/json", summary="DWG-to-JSON output")
def get_json_artifact(drawing_version_id: str):
    return _serve_artifact(
        drawing_version_id, "json", media_type="application/json"
    )
