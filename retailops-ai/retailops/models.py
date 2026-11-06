"""Transactional source tables, exception workflow and immutable status audit events."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from retailops.database import Base


def utc_now():
    return datetime.now(timezone.utc)


def uid():
    return uuid4().hex


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(60), index=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))


class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    sale_date: Mapped[datetime] = mapped_column(Date, index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_eur: Mapped[float] = mapped_column(Float)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id", "snapshot_date", name="uq_inventory_snapshot"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    snapshot_date: Mapped[datetime] = mapped_column(Date)
    expected_qty: Mapped[int] = mapped_column(Integer)
    counted_qty: Mapped[int] = mapped_column(Integer)


class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    expected_date: Mapped[datetime] = mapped_column(Date)
    actual_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("kind", "source_ref", name="uq_issue_origin"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=uid)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    source_ref: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(16), default="OPEN", index=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=uid)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id"), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    old_status: Mapped[str] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
