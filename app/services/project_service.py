# app/services/project_service.py
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session  # kept for future compatibility

from app.schemas.projects import ProjectCreate, ProjectItem, ProjectListResponse

logger = logging.getLogger(__name__)

# NOTE:
# This is a NON-PERSISTENT placeholder implementation.
# It does NOT store anything in the database yet.
# It only returns stub responses so the API and frontend can be wired up.


def create_project(db: Session, data: ProjectCreate) -> ProjectItem:
    """
    Placeholder project creation.

    Currently:
    - Does NOT persist anything to the database
    - Returns a synthetic project item

    Later:
    - Insert a Project row in Postgres
    - Link drawings to projects via association table
    """
    project_id = str(uuid.uuid4())
    logger.debug(
        "Creating project (placeholder) name=%s description=%s project_id=%s",
        data.name,
        data.description,
        project_id,
    )

    now = datetime.utcnow()
    return ProjectItem(
        project_id=project_id,
        name=data.name,
        description=data.description,
        created_at=now,
        active=True,
    )


def list_projects(db: Session) -> ProjectListResponse:
    """
    Placeholder list: always returns an empty list.
    """
    logger.debug("Listing projects (placeholder, always empty)")
    items: List[ProjectItem] = []
    return ProjectListResponse(items=items)


def delete_project(db: Session, project_id: str) -> bool:
    """
    Placeholder delete: always returns False so router returns 404.
    """
    logger.debug("Deleting project project_id=%s (placeholder, no-op)", project_id)
    return False
