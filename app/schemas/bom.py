from typing import List
from pydantic import BaseModel


class BomItemSchema(BaseModel):
    item_number: int | None = None
    part_number: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit: str | None = None
    notes: str | None = None


class BomResponse(BaseModel):
    items: List[BomItemSchema]
    status: str  # "not_implemented" | "ok" later
