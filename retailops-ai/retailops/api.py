"""FastAPI backend for operational reporting and controlled issue review."""
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from retailops.analytics import metrics, issue_list
from retailops.ai import rule_based_insight, llm_insight
from retailops.config import API_KEY
from retailops.database import get_db
from retailops.models import Issue, AuditEvent
from retailops.schemas import IssueUpdate

app = FastAPI(title="RetailOps AI", version="1.0.0", description="Fictional multi-site retail operations demo")
DB = Annotated[Session, Depends(get_db)]

ALLOWED_TRANSITIONS = {
    "OPEN": {"IN_REVIEW", "DISMISSED"},
    "IN_REVIEW": {"RESOLVED", "DISMISSED"},
    "RESOLVED": set(),
    "DISMISSED": set(),
}


def require_api_key(x_api_key: Annotated[str | None, Header()] = None):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API_KEY not configured; writes disabled")
    if not x_api_key or not compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/regions")
def regions():
    return ["Germany", "France", "Netherlands"]


@app.get("/api/metrics")
def get_metrics(db: DB, region: str | None = Query(default=None, max_length=60)):
    return metrics(db, region)


@app.get("/api/issues")
def get_issues(db: DB, region: str | None = None, status: str | None = None):
    return issue_list(db, region, status)


@app.get("/api/issues/{issue_id}/audit")
def audit(issue_id: str, db: DB, _: None = Depends(require_api_key)):
    items = db.scalars(select(AuditEvent).where(AuditEvent.issue_id == issue_id)
                       .order_by(AuditEvent.changed_at)).all()
    return [{"actor": e.actor, "old_status": e.old_status, "new_status": e.new_status,
             "note": e.note, "changed_at": e.changed_at.isoformat()} for e in items]


@app.patch("/api/issues/{issue_id}")
def update_issue(issue_id: str, payload: IssueUpdate, db: DB,
                 _: None = Depends(require_api_key)):
    item = db.get(Issue, issue_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if payload.status not in ALLOWED_TRANSITIONS.get(item.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid status transition: {item.status} -> {payload.status}")
    old = item.status
    item.status = payload.status
    item.updated_at = datetime.now(timezone.utc)
    db.add(AuditEvent(issue_id=issue_id, actor=payload.actor.strip(), old_status=old,
                      new_status=payload.status, note=payload.note.strip()))
    db.commit()
    return {"id": item.id, "old_status": old, "status": item.status, "recorded": True}


@app.get("/api/insights")
def insights(db: DB, region: str | None = None):
    return rule_based_insight(metrics(db, region))


@app.post("/api/insights/ai")
def generate_ai_insights(db: DB, region: str | None = None,
                         _: None = Depends(require_api_key)):
    try:
        return llm_insight(metrics(db, region))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Never return third-party exceptions containing request bodies or credentials.
        raise HTTPException(status_code=502, detail="LLM request failed; use /api/insights instead") from exc
