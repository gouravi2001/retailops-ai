"""Create demo DB and seed fictional data the first time the application runs."""
from pathlib import Path
from sqlalchemy import select
from retailops.database import SessionLocal, create_tables
from retailops.generate_data import generate_demo_csv
from retailops.ingest import ingest_directory
from retailops.models import Store
from retailops.anomalies import build_issues


def bootstrap(folder: Path = Path("data/sample")) -> dict:
    create_tables()
    with SessionLocal() as db:
        exists = db.scalar(select(Store.id).limit(1))
        if exists:
            return {"seeded": False, "reason": "Database already contains stores"}
        generated = generate_demo_csv(folder)
        counts = ingest_directory(db, folder)
        created_issues = build_issues(db)
        return {"seeded": True, "rows": counts, "issues": created_issues,
                "csv_files": [str(path) for path in generated.values()]}


if __name__ == "__main__":
    print(bootstrap())
