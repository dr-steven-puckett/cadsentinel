from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.customers import Customer

logger = logging.getLogger(__name__)


def list_customers(
    db: Session,
    *,
    q: Optional[str] = None,
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Customer], int]:
    stmt = select(Customer)
    count_stmt = select(func.count()).select_from(Customer)

    if active_only:
        stmt = stmt.where(Customer.active.is_(True))
        count_stmt = count_stmt.where(Customer.active.is_(True))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Customer.name.ilike(like)) | (Customer.code.ilike(like)))
        count_stmt = count_stmt.where((Customer.name.ilike(like)) | (Customer.code.ilike(like)))

    stmt = stmt.order_by(Customer.created_at.desc()).limit(limit).offset(offset)

    items = list(db.execute(stmt).scalars().all())
    total = int(db.execute(count_stmt).scalar_one())
    return items, total


def create_customer(db: Session, *, name: str, code: Optional[str], contact_info: Optional[str]) -> Customer:
    customer = Customer(name=name.strip(), code=(code.strip() if code else None), contact_info=contact_info)
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # usually duplicate code (unique) or other constraint
        raise ValueError("Customer could not be created (possible duplicate code).")
    db.refresh(customer)
    return customer


def get_customer(db: Session, *, customer_id: UUID) -> Customer | None:
    stmt = select(Customer).where(Customer.id == customer_id)
    return db.execute(stmt).scalars().first()


def update_customer(db: Session, *, customer_id: UUID, **fields) -> Customer:
    customer = get_customer(db, customer_id=customer_id)
    if not customer:
        raise KeyError("Customer not found.")

    for k, v in fields.items():
        if v is None:
            continue
        setattr(customer, k, v)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Customer could not be updated (possible duplicate code).")
    db.refresh(customer)
    return customer


def delete_customer(db: Session, *, customer_id: UUID, hard: bool = False) -> None:
    customer = get_customer(db, customer_id=customer_id)
    if not customer:
        raise KeyError("Customer not found.")

    if hard:
        db.delete(customer)
    else:
        customer.active = False

    db.commit()
