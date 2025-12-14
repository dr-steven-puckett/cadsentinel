from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.customers import (
    CustomerCreate,
    CustomerItem,
    CustomerListResponse,
    CustomerUpdate,
)
from app.services import customers_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(
    q: str | None = Query(default=None, description="Search by name or code"),
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CustomerListResponse:
    items, total = customers_service.list_customers(
        db, q=q, active_only=active_only, limit=limit, offset=offset
    )
    return CustomerListResponse(items=items, total=total)


@router.post("", response_model=CustomerItem, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> CustomerItem:
    try:
        return customers_service.create_customer(
            db, name=payload.name, code=payload.code, contact_info=payload.contact_info
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{customer_id}", response_model=CustomerItem)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)) -> CustomerItem:
    customer = customers_service.get_customer(db, customer_id=customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerItem)
def update_customer(customer_id: UUID, payload: CustomerUpdate, db: Session = Depends(get_db)) -> CustomerItem:
    try:
        return customers_service.update_customer(db, customer_id=customer_id, **payload.model_dump(exclude_unset=True))
    except KeyError:
        raise HTTPException(status_code=404, detail="Customer not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: UUID,
    hard: bool = Query(default=False, description="Hard delete row (default soft-deletes by setting active=false)"),
    db: Session = Depends(get_db),
) -> None:
    try:
        customers_service.delete_customer(db, customer_id=customer_id, hard=hard)
    except KeyError:
        raise HTTPException(status_code=404, detail="Customer not found")
