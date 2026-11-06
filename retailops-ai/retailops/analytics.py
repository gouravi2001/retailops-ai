"""Operational metric definitions, computed from approved structured records."""
from collections import defaultdict
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from retailops.models import Store, Sale, Inventory, Delivery, Issue

ACTIVE_STATUSES = {"OPEN", "IN_REVIEW"}


def pct(numerator: float, denominator: float) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def metrics(db: Session, region: str | None = None) -> dict:
    query = select(Store).order_by(Store.region, Store.name)
    if region and region != "All regions":
        query = query.where(Store.region == region)
    stores = list(db.scalars(query).all())
    ids = [store.id for store in stores]
    if not ids:
        return {"summary": {"revenue_eur": 0, "inventory_accuracy_pct": None,
                            "on_time_delivery_pct": None, "active_issues": 0, "stores_tracked": 0},
                "by_store": [], "daily_sales": []}

    sales = db.scalars(select(Sale).where(Sale.store_id.in_(ids))).all()
    inventory = db.scalars(select(Inventory).where(Inventory.store_id.in_(ids))).all()
    deliveries = db.scalars(select(Delivery).where(Delivery.store_id.in_(ids))).all()
    issues = db.scalars(select(Issue).where(Issue.store_id.in_(ids))).all()

    # Each store/product uses only its latest inventory snapshot.
    latest = {}
    for row in inventory:
        key = (row.store_id, row.product_id)
        if key not in latest or row.snapshot_date >= latest[key].snapshot_date:
            latest[key] = row
    by_store = []
    revenue_total, expected_total, discrepancy_total = 0, 0, 0
    delivered_total, on_time_total, active_total = 0, 0, 0
    daily = defaultdict(float)
    for store in stores:
        store_sales = [s for s in sales if s.store_id == store.id]
        store_inv = [i for i in latest.values() if i.store_id == store.id]
        store_del = [d for d in deliveries if d.store_id == store.id and d.actual_date is not None]
        store_issues = [i for i in issues if i.store_id == store.id and i.status in ACTIVE_STATUSES]
        revenue = round(sum(s.quantity * s.unit_price_eur for s in store_sales), 2)
        expected = sum(row.expected_qty for row in store_inv)
        discrepancy = sum(abs(row.expected_qty - row.counted_qty) for row in store_inv)
        on_time = sum(d.actual_date <= d.expected_date for d in store_del)
        by_store.append({
            "store_id": store.id, "store_name": store.name, "city": store.city,
            "region": store.region, "revenue_eur": revenue,
            "inventory_accuracy_pct": pct(max(0, expected - discrepancy), expected),
            "on_time_delivery_pct": pct(on_time, len(store_del)),
            "active_issues": len(store_issues),
        })
        revenue_total += revenue
        expected_total += expected
        discrepancy_total += discrepancy
        delivered_total += len(store_del)
        on_time_total += on_time
        active_total += len(store_issues)
        for sale in store_sales:
            daily[sale.sale_date.isoformat()] += sale.quantity * sale.unit_price_eur

    return {
        "summary": {
            "revenue_eur": round(revenue_total, 2),
            "inventory_accuracy_pct": pct(max(0, expected_total - discrepancy_total), expected_total),
            "on_time_delivery_pct": pct(on_time_total, delivered_total),
            "active_issues": active_total,
            "stores_tracked": len(stores),
        },
        "by_store": by_store,
        "daily_sales": [{"date": day, "revenue_eur": round(value, 2)} for day, value in sorted(daily.items())],
        "definitions": {
            "inventory_accuracy_pct": "100 × (1 - sum(abs(expected-counted)) / sum(expected)) for latest store/product snapshots, clamped at 0",
            "on_time_delivery_pct": "Percentage of completed deliveries arriving on or before expected date; pending excluded",
            "active_issues": "Issues with status OPEN or IN_REVIEW",
        },
    }


def issue_list(db: Session, region: str | None = None, status: str | None = None) -> list[dict]:
    stmt = select(Issue, Store).join(Store, Store.id == Issue.store_id)
    if region and region != "All regions":
        stmt = stmt.where(Store.region == region)
    if status and status != "All":
        stmt = stmt.where(Issue.status == status)
    stmt = stmt.order_by(Issue.created_at.desc(), Issue.id)
    return [{
        "id": i.id, "store_id": i.store_id, "store_name": s.name, "region": s.region,
        "kind": i.kind, "severity": i.severity, "status": i.status,
        "description": i.description, "source_ref": i.source_ref,
        "created_at": i.created_at.isoformat(),
    } for i, s in db.execute(stmt).all()]
