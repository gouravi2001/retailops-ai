"""Validate all input data first, then upsert inside a single DB transaction."""
import argparse
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from retailops.data_quality import validate_frame, validate_references
from retailops.database import SessionLocal, create_tables
from retailops.models import Store, Product, Sale, Inventory, Delivery

MAP = {
    "stores": (Store, ["id", "name", "city", "region"]),
    "products": (Product, ["id", "name", "category"]),
    "sales": (Sale, ["id", "store_id", "product_id", "sale_date", "quantity", "unit_price_eur"]),
    "inventory": (Inventory, ["id", "store_id", "product_id", "snapshot_date", "expected_qty", "counted_qty"]),
    "deliveries": (Delivery, ["id", "store_id", "product_id", "expected_date", "actual_date", "quantity"]),
}


def read_and_validate(directory: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in MAP:
        path = Path(directory) / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing input: {path}")
        frame = pd.read_csv(path, dtype={"id": "string", "store_id": "string", "product_id": "string"})
        frames[name] = validate_frame(name, frame)
    validate_references(frames)
    return frames


def ingest_frames(db: Session, frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Upsert by stable primary key; re-importing the same CSV does not duplicate rows."""
    counts = {}
    for name, (model, fields) in MAP.items():
        frame = frames[name]
        for row in frame.to_dict(orient="records"):
            payload = {key: row[key] for key in fields}
            for date_field in ("sale_date", "snapshot_date", "expected_date", "actual_date"):
                if date_field in payload:
                    value = payload[date_field]
                    payload[date_field] = None if pd.isna(value) else pd.Timestamp(value).date()
            db.merge(model(**payload))
        db.flush()
        counts[name] = len(frame)
    return counts


def ingest_directory(db: Session, directory: Path) -> dict[str, int]:
    frames = read_and_validate(directory)
    try:
        counts = ingest_frames(db, frames)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate and import CSVs")
    parser.add_argument("--dir", default="data/sample")
    args = parser.parse_args()
    create_tables()
    with SessionLocal() as session:
        print("Loaded:", ingest_directory(session, Path(args.dir)))
