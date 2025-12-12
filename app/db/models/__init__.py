# app/db/models/__init__.py

from app.db.base import Base

# Core drawing-related models (from core.py)
from .core import (
    Drawing,
    DrawingVersion,
    DrawingFile,
    DrawingSummary,
    Dimension,
    Note,
    Embedding,
    EngineeringStandard,
    StandardRule,
    StandardViolation,
)

# Additional tables from submodules
from .bom import BomItem
from .customers import Customer
from .projects import Project
from .issues import DrawingIssue
from .standards import StandardDocument
from .associations import drawing_projects, drawing_customers
from .drawing_chunk import DrawingTextChunk

__all__ = [
    "Base",
    "Drawing",
    "DrawingVersion",
    "DrawingFile",
    "DrawingSummary",
    "Dimension",
    "Note",
    "Embedding",
    "EngineeringStandard",
    "StandardRule",
    "StandardViolation",
    "BomItem",
    "Customer",
    "Project",
    "DrawingIssue",
    "StandardDocument",
    "drawing_projects",
    "drawing_customers",
]

__all__.append("DrawingTextChunk")
