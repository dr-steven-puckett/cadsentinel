# app/schemas/projects.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    """
    Payload for creating a new project.
    """
    name: str
    description: Optional[str] = None


class ProjectItem(BaseModel):
    """
    A single project, as returned to the frontend.
    """
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    active: bool


class ProjectListResponse(BaseModel):
    """
    List response wrapper for projects.
    """
    items: List[ProjectItem]
