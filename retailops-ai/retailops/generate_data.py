"""Make reproducible, entirely fictional retail datasets. No real people/customer data."""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

STORES = [
    ("DE01", "Elbe Central", "Hamburg", "Germany"),
    ("DE02", "Spree Market", "Berlin", "Germany"),
    ("DE03", "Isar Retail", "Munich", "Germany"),
    ("FR01", "Seine Centre", "Paris", "France"),
    ("FR02", "Rhone Plaza", "Lyon", "France"),
    ("FR03", "Lille North", "Lille", "France"),
    ("NL01", "Canal Market", "Amsterdam", "Netherlands"),
    ("NL02", "Maas Shop", "Rotterdam", "Netherlands"),
    ("NL03", "Utrecht Point", "Utrecht", "Netherlands"),
]
PRODUCTS = [
    ("P001", "Notebook", "Office", 5.49),
    ("P002", "Desk Lamp", "Home", 19.99),
    ("P003", "Water Bottle", "Lifestyle", 12.75),
    ("P004", "Phone Stand", "Electronics", 9.95),
    ("P005", "Keyboard", "Electronics", 31.50),
    ("P006", "Reusable Bag", "Lifestyle", 3.99),
    ("P007", "USB Cable", "Electronics", 7.80),
    ("P008", "Storage Box", "Home", 14.60),
    ("P009", "Travel Mug", "Lifestyle", 17.50),
    ("P010", "Pen Set", "Office", 8.20),
]


def generate_demo_csv(output_dir: Path, seed: int = 42, end_date: date | None = None) -> dict[str, Path]:
    rng = random.Random(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    end_date = end_date or date.today()
    pd.DataFrame(STORES, columns=["id", "name", "city", "region"]).to_csv(output_dir / "stores.csv", index=False)
    pd.DataFrame([p[:3] for p in PRODUCTS], columns=["id", "name", "category"]).to_csv(output_dir / "products.csv", index=False)

    sales, inventory, deliveries = [], [], []
    sale_num = delivery_num = 0
    for store_id, _, _, region in STORES:
        for delta in range(29, -1, -1):
            day = end_date - timedelta(days=delta)
            for _ in range(rng.randint(3, 7)):
                sale_num += 1
                product = rng.choice(PRODUCTS)
                sales.append({
                    "id": f"S{sale_num:06d}", "store_id": store_id, "product_id": product[0],
                    "sale_date": day.isoformat(), "quantity": rng.randint(1, 8),
                    "unit_price_eur": product[3],
                })
            for _ in range(2):
                delivery_num += 1
                product = rng.choice(PRODUCTS)
                due_date = day
                if rng.random() < 0.10 and delta < 7:
                    actual = ""  # still pending, may be overdue
                else:
                    actual = (due_date + timedelta(days=rng.choice([-1, 0, 0, 0, 1, 2, 3]))).isoformat()
                deliveries.append({
                    "id": f"D{delivery_num:06d}", "store_id": store_id, "product_id": product[0],
                    "expected_date": due_date.isoformat(), "actual_date": actual,
                    "quantity": rng.randint(5, 50),
                })
        for product_id, *_ in PRODUCTS:
            expected = rng.randint(20, 140)
            if rng.random() < (0.35 if region == "France" else 0.17):
                counted = max(0, expected + rng.choice([-19, -14, -9, 8, 13, 18]))
            else:
                counted = expected + rng.choice([-1, 0, 0, 0, 1])
            inventory.append({
                "id": f"I{store_id}{product_id}", "store_id": store_id, "product_id": product_id,
                "snapshot_date": end_date.isoformat(), "expected_qty": expected,
                "counted_qty": counted,
            })
    pd.DataFrame(sales).to_csv(output_dir / "sales.csv", index=False)
    pd.DataFrame(inventory).to_csv(output_dir / "inventory.csv", index=False)
    pd.DataFrame(deliveries).to_csv(output_dir / "deliveries.csv", index=False)
    return {name: output_dir / f"{name}.csv" for name in ("stores", "products", "sales", "inventory", "deliveries")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fake retail CSVs")
    parser.add_argument("--out", default="data/sample")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generated = generate_demo_csv(Path(args.out), args.seed)
    for path in generated.values():
        print(path)
