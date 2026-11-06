import pandas as pd
import pytest
from retailops.generate_data import generate_demo_csv
from retailops.ingest import read_and_validate, ingest_directory


def test_generated_data_valid(tmp_path):
    generate_demo_csv(tmp_path)
    frames = read_and_validate(tmp_path)
    assert len(frames["stores"]) == 9
    assert len(frames["products"]) == 10
    assert len(frames["sales"]) > 100


def test_negative_quantity_rejected(tmp_path):
    generate_demo_csv(tmp_path)
    path = tmp_path / "sales.csv"
    sales = pd.read_csv(path)
    sales.loc[0, "quantity"] = -5
    sales.to_csv(path, index=False)
    with pytest.raises((ValueError, Exception), match="quantity"):
        read_and_validate(tmp_path)


def test_unknown_store_rejected(tmp_path):
    generate_demo_csv(tmp_path)
    path = tmp_path / "sales.csv"
    sales = pd.read_csv(path)
    sales.loc[0, "store_id"] = "NOT_A_STORE"
    sales.to_csv(path, index=False)
    with pytest.raises(ValueError, match="unknown store"):
        read_and_validate(tmp_path)


def test_ingest_is_idempotent(db, tmp_path):
    from sqlalchemy import select, func
    from retailops.models import Sale
    generate_demo_csv(tmp_path)
    first = ingest_directory(db, tmp_path)
    second = ingest_directory(db, tmp_path)
    rows = db.scalar(select(func.count()).select_from(Sale))
    assert first["sales"] == second["sales"] == rows
