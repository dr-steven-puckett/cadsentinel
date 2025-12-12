from typing import List, Dict, Any
from pydantic import BaseModel


class BatchChatRequest(BaseModel):
    drawing_version_ids: List[str]
    message: str
    max_tokens: int | None = 1024


class BatchChatResponse(BaseModel):
    reply: str
    used_drawings: List[str]
    trace: Dict[str, Any] = {}


class SimilarDrawingsResponseItem(BaseModel):
    drawing_version_id: str
    score: float
    thumbnail_url: str
    png_url: str


class SimilarDrawingsResponse(BaseModel):
    query_drawing_version_id: str
    items: List[SimilarDrawingsResponseItem]


class HeatmapRegion(BaseModel):
    x: float
    y: float
    width: float
    height: float
    score: float
    label: str | None = None


class RetrievalHeatmapResponse(BaseModel):
    drawing_version_id: str
    query: str
    regions: List[HeatmapRegion]


class ExplainDrawingResponse(BaseModel):
    drawing_version_id: str
    explanation: str
    sections: Dict[str, str]  # section_title -> text


class RubricValidationRequest(BaseModel):
    rubric_id: str
    strict: bool = False


class RubricValidationResult(BaseModel):
    rubric_id: str
    passed: bool
    score: float
    messages: List[str]


class AssemblyItem(BaseModel):
    drawing_version_id: str
    role: str  # "parent" | "child"
    relation: str | None = None


class AssemblyResponse(BaseModel):
    assembly_id: str
    items: List[AssemblyItem]
    status: str
