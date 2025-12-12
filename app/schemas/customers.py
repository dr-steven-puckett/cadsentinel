# app/schemas/customers.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CustomerCreate(BaseModel):
    """
    Payload for creating a new customer.
    """
    name: str
    code: Optional[str] = None
    contact_info: Optional[str] = None


class CustomerItem(BaseModel):
    """
    A single customer, as returned to the frontend.
    """
    customer_id: str
    name: str
    code: Optional[str] = None
    contact_info: Optional[str] = None
    created_at: datetime
    active: bool


class CustomerListResponse(BaseModel):
    """
    List response wrapper for customers.
    """
    items: List[CustomerItem]
