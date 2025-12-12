# app/api/routers/customers.py
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.customers import (
    CustomerCreate,
    CustomerItem,
    CustomerListResponse,
)
from app.services import customer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post(
    "",
    response_model=CustomerItem,
    summary="Create customer",
    description="Create a new customer record (placeholder implementation).",
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
) -> CustomerItem:
    """
    Create a new customer.

    Currently:
    - Uses a placeholder service that does NOT persist to the database.
    - Returns a synthetic CustomerItem with a generated UUID.

    Later:
    - Will insert a Customer row in Postgres.
    - Optionally link drawings to this customer.
    """
    customer = customer_service.create_customer(db, data)
    logger.debug("Created customer_id=%s name=%s", customer.customer_id, customer.name)
    return customer


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers",
    description="List all customers (placeholder implementation, always empty for now).",
)
def list_customers(
    db: Session = Depends(get_db),
) -> CustomerListResponse:
    """
    List customers.

    Currently:
    - Returns an empty list via the placeholder service.
    """
    return customer_service.list_customers(db)


@router.delete(
    "/{customer_id}",
    status_code=204,
    summary="Delete customer",
    description="Delete a customer by ID (placeholder, always returns 404).",
)
def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a customer.

    Currently:
    - Placeholder implementation; always returns 404 via the router.
    """
    ok = customer_service.delete_customer(db, customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")
    logger.debug("Deleted customer_id=%s", customer_id)
    return
