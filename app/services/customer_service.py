# app/services/customer_service.py
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session  # kept for future compatibility

from app.schemas.customers import (
    CustomerCreate,
    CustomerItem,
    CustomerListResponse,
)

logger = logging.getLogger(__name__)

# NOTE:
# This is a NON-PERSISTENT placeholder implementation.
# It does NOT store anything in the database yet.
# It only returns stub responses so the API and frontend can be wired up.


def create_customer(db: Session, data: CustomerCreate) -> CustomerItem:
    """
    Placeholder customer creation.

    Currently:
    - Does NOT persist anything to the database
    - Returns a synthetic customer item

    Later:
    - Insert a Customer row in Postgres
    - Link drawings to customers via association table
    """
    customer_id = str(uuid.uuid4())
    logger.debug(
        "Creating customer (placeholder) name=%s code=%s customer_id=%s",
        data.name,
        data.code,
        customer_id,
    )

    now = datetime.utcnow()
    return CustomerItem(
        customer_id=customer_id,
        name=data.name,
        code=data.code,
        contact_info=data.contact_info,
        created_at=now,
        active=True,
    )


def list_customers(db: Session) -> CustomerListResponse:
    """
    Placeholder list: always returns an empty list.
    """
    logger.debug("Listing customers (placeholder, always empty)")
    items: List[CustomerItem] = []
    return CustomerListResponse(items=items)


def delete_customer(db: Session, customer_id: str) -> bool:
    """
    Placeholder delete: always returns False so router returns 404.
    """
    logger.debug("Deleting customer customer_id=%s (placeholder, no-op)", customer_id)
    return False
