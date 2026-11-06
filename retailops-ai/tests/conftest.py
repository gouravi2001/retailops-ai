import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from retailops.database import Base, get_db
from retailops.api import app
from retailops.generate_data import generate_demo_csv
from retailops.ingest import ingest_directory
from retailops.anomalies import build_issues
import retailops.api as api_module


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    local = sessionmaker(bind=engine, expire_on_commit=False)
    with local() as session:
        yield session
    engine.dispose()


@pytest.fixture
def populated(db, tmp_path):
    generate_demo_csv(tmp_path)
    ingest_directory(db, tmp_path)
    build_issues(db)
    return db


@pytest.fixture
def client(populated, monkeypatch):
    monkeypatch.setattr(api_module, "API_KEY", "integration-test-key")

    def override_db():
        yield populated

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
