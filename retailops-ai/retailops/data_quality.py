"""Strict Pandas validation; Pandera also enforces declarative schemas when installed."""
import pandas as pd
try:
    import pandera.pandas as pa
except ImportError:  # allows basic offline CI tests without optional validator
    pa = None

REQUIRED = {
    "stores": ["id", "name", "city", "region"],
    "products": ["id", "name", "category"],
    "sales": ["id", "store_id", "product_id", "sale_date", "quantity", "unit_price_eur"],
    "inventory": ["id", "store_id", "product_id", "snapshot_date", "expected_qty", "counted_qty"],
    "deliveries": ["id", "store_id", "product_id", "expected_date", "actual_date", "quantity"],
}
DATE_COLUMNS = {
    "sales": ["sale_date"], "inventory": ["snapshot_date"],
    "deliveries": ["expected_date", "actual_date"],
}
NONNEG = {"sales": ["unit_price_eur"], "inventory": ["expected_qty", "counted_qty"]}
POSITIVE = {"sales": ["quantity"], "deliveries": ["quantity"]}
VALID_REGIONS = {"Germany", "France", "Netherlands"}

if pa is not None:
    C = pa.Check
    SCHEMAS = {
        "stores": pa.DataFrameSchema({
            "id": pa.Column(str, nullable=False, unique=True),
            "name": pa.Column(str, nullable=False),
            "city": pa.Column(str, nullable=False),
            "region": pa.Column(str, C.isin(list(VALID_REGIONS))),
        }, strict=True),
        "products": pa.DataFrameSchema({
            "id": pa.Column(str, nullable=False, unique=True),
            "name": pa.Column(str), "category": pa.Column(str),
        }, strict=True),
        "sales": pa.DataFrameSchema({
            "id": pa.Column(str, nullable=False, unique=True),
            "store_id": pa.Column(str), "product_id": pa.Column(str),
            "sale_date": pa.Column("datetime64[ns]"),
            "quantity": pa.Column(int, C.gt(0), coerce=True),
            "unit_price_eur": pa.Column(float, C.ge(0), coerce=True),
        }, strict=True),
        "inventory": pa.DataFrameSchema({
            "id": pa.Column(str, nullable=False, unique=True),
            "store_id": pa.Column(str), "product_id": pa.Column(str),
            "snapshot_date": pa.Column("datetime64[ns]"),
            "expected_qty": pa.Column(int, C.ge(0), coerce=True),
            "counted_qty": pa.Column(int, C.ge(0), coerce=True),
        }, strict=True),
        "deliveries": pa.DataFrameSchema({
            "id": pa.Column(str, nullable=False, unique=True),
            "store_id": pa.Column(str), "product_id": pa.Column(str),
            "expected_date": pa.Column("datetime64[ns]"),
            "actual_date": pa.Column("datetime64[ns]", nullable=True),
            "quantity": pa.Column(int, C.gt(0), coerce=True),
        }, strict=True),
    }


def validate_frame(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Reject missing columns, bad numeric/dates, duplicate keys, unknown categories."""
    if name not in REQUIRED:
        raise ValueError(f"Unknown dataset: {name}")
    expected = set(REQUIRED[name])
    if set(frame.columns) != expected:
        raise ValueError(f"Column mismatch in {name}; missing={expected - set(frame.columns)}, extra={set(frame.columns)-expected}")
    frame = frame.copy()
    for text_col in [col for col in REQUIRED[name] if col in ("id", "store_id", "product_id", "name", "city", "region", "category")]:
        if frame[text_col].isna().any() or frame[text_col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing or blank values in {name}.{text_col}")
        frame[text_col] = frame[text_col].astype(str)
    if frame["id"].duplicated().any():
        raise ValueError(f"Duplicate ID values in {name}")
    for col in DATE_COLUMNS.get(name, []):
        original = frame[col]
        frame[col] = pd.to_datetime(original, errors="coerce")
        if col != "actual_date" and frame[col].isna().any():
            raise ValueError(f"Invalid or missing date in {name}.{col}")
        if col == "actual_date" and (original.notna() & frame[col].isna()).any():
            raise ValueError(f"Invalid non-empty date in {name}.{col}")
    for col in NONNEG.get(name, []) + POSITIVE.get(name, []):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
        if frame[col].isna().any():
            raise ValueError(f"Missing or invalid number in {name}.{col}")
        floor = 1 if col in POSITIVE.get(name, []) else 0
        if (frame[col] < floor).any():
            raise ValueError(f"Out-of-range value in {name}.{col}")
        if col != "unit_price_eur":
            if (frame[col] % 1 != 0).any():
                raise ValueError(f"Fractional count in {name}.{col}")
            frame[col] = frame[col].astype(int)
        else:
            frame[col] = frame[col].astype(float)
    if name == "stores" and not set(frame["region"]).issubset(VALID_REGIONS):
        raise ValueError("Unknown retail region")
    if pa is not None:
        return SCHEMAS[name].validate(frame, lazy=True)
    return frame


def validate_references(frames: dict[str, pd.DataFrame]) -> None:
    stores, products = set(frames["stores"]["id"]), set(frames["products"]["id"])
    for name in ("sales", "inventory", "deliveries"):
        if not set(frames[name]["store_id"]).issubset(stores):
            raise ValueError(f"{name} references unknown store IDs")
        if not set(frames[name]["product_id"]).issubset(products):
            raise ValueError(f"{name} references unknown product IDs")
    inv = frames["inventory"]
    if inv.duplicated(["store_id", "product_id", "snapshot_date"]).any():
        raise ValueError("Duplicate inventory snapshot for store/product/date")
