"""Deterministic exception detection: no LLM decides whether an issue exists."""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from retailops.models import Inventory, Delivery, Issue


def inventory_exception(expected: int, counted: int) -> bool:
    """Flag both material absolute and relative stock discrepancies."""
    return abs(expected - counted) >= 3 and (expected == 0 or abs(expected - counted) / expected >= 0.08)


def delivery_exception(expected: date, actual: date | None, as_of: date) -> bool:
    """Flag deliveries >2 days late, including outstanding overdue deliveries."""
    return (actual - expected).days > 2 if actual else (as_of - expected).days > 2


def build_issues(db: Session, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    created = 0
    existing = {(issue.kind, issue.source_ref) for issue in db.scalars(select(Issue)).all()}
    for stock in db.scalars(select(Inventory)).all():
        if not inventory_exception(stock.expected_qty, stock.counted_qty):
            continue
        key = ("INVENTORY", stock.id)
        if key not in existing:
            difference = stock.counted_qty - stock.expected_qty
            db.add(Issue(
                store_id=stock.store_id, kind=key[0], source_ref=key[1],
                severity="HIGH" if abs(difference) >= 14 else "MEDIUM",
                description=(f"Product {stock.product_id}: expected {stock.expected_qty}, "
                             f"counted {stock.counted_qty}, difference {difference:+d}."),
            ))
            created += 1
            existing.add(key)
    for delivery in db.scalars(select(Delivery)).all():
        if not delivery_exception(delivery.expected_date, delivery.actual_date, as_of):
            continue
        key = ("DELIVERY", delivery.id)
        if key not in existing:
            days = ((delivery.actual_date or as_of) - delivery.expected_date).days
            db.add(Issue(
                store_id=delivery.store_id, kind=key[0], source_ref=key[1],
                severity="HIGH" if days >= 5 else "MEDIUM",
                description=f"Delivery {delivery.id} for {delivery.product_id} late by {days} days.",
            ))
            created += 1
            existing.add(key)
    db.commit()
    return created
