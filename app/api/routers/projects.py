import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.projects import ProjectCreate, ProjectItem, ProjectListResponse
from app.services import project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectItem, summary="Create project")
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return project_service.create_project(db, data)


@router.get("", response_model=ProjectListResponse, summary="List projects")
def list_projects(db: Session = Depends(get_db)):
    return project_service.list_projects(db)


@router.delete("/{project_id}", status_code=204, summary="Delete project")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    ok = project_service.delete_project(db, project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return
