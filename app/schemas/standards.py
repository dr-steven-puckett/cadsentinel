from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StandardUploadResponse(BaseModel):
    standard_id: str
    filename: str
    summary: Optional[str] = None
    extracted_rules: List[Dict[str, Any]] = []
    embedding_stats: Dict[str, Any] = {}


class StandardListItem(BaseModel):
    standard_id: str
    name: str
    filename: str
    date_uploaded: datetime


class StandardListResponse(BaseModel):
    items: List[StandardListItem]


class StandardDetail(BaseModel):
    standard_id: str
    name: str
    filename: str
    summary: Optional[str]
    extracted_rules: List[Dict[str, Any]]
    available_rule_types: List[str]
    date_uploaded: datetime
