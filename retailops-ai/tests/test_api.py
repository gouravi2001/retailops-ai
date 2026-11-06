
def test_metrics_and_issues(client):
    r = client.get("/api/metrics", params={"region": "France"})
    assert r.status_code == 200
    assert r.json()["summary"]["stores_tracked"] == 3
    issues = client.get("/api/issues").json()
    assert len(issues) > 0


def test_write_requires_key(client):
    issue_id = client.get("/api/issues").json()[0]["id"]
    body = {"status": "IN_REVIEW", "actor": "QA reviewer", "note": "Checked supporting store evidence"}
    response = client.patch(f"/api/issues/{issue_id}", json=body)
    assert response.status_code == 401


def test_review_then_resolve_with_audit(client):
    issue = next(i for i in client.get("/api/issues").json() if i["status"] == "OPEN")
    url = f"/api/issues/{issue['id']}"
    headers = {"X-API-Key": "integration-test-key"}
    bad = client.patch(url, headers=headers, json={
        "status": "RESOLVED", "actor": "QA reviewer", "note": "Evidence fully verified"
    })
    assert bad.status_code == 409
    review = client.patch(url, headers=headers, json={
        "status": "IN_REVIEW", "actor": "QA reviewer", "note": "Investigating warehouse count"
    })
    assert review.status_code == 200
    done = client.patch(url, headers=headers, json={
        "status": "RESOLVED", "actor": "QA reviewer", "note": "Reconciled with recount records"
    })
    assert done.status_code == 200
    audit = client.get(f"{url}/audit", headers=headers)
    assert [event["new_status"] for event in audit.json()] == ["IN_REVIEW", "RESOLVED"]


def test_llm_endpoint_is_explicit_and_secured(client, monkeypatch):
    import retailops.ai as ai_module
    monkeypatch.setattr(ai_module, "OPENAI_API_KEY", "")
    assert client.post("/api/insights/ai").status_code == 401
    response = client.post("/api/insights/ai", headers={"X-API-Key": "integration-test-key"})
    assert response.status_code == 503  # no external key in test environment
