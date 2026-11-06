# Live demonstration and user training walkthrough

This script demonstrates the skills relevant to an interactive operations/quality dashboard role. Allow about 8–12 minutes for a live walkthrough, depending on discussion.

## Preparation

1. Run `docker compose up --build` or the SQLite local setup.
2. Check the API health endpoint and open the Streamlit dashboard.
3. Keep the API docs page at `/docs` open in another tab.
4. Be ready to use an issue ID and your local test API key.

## 1 — Explain the problem

"Nine sites in three regions submit sales, stock and delivery data. My pipeline validates and centralizes their inputs, while the dashboard presents consistent operational KPIs and helps users investigate exceptions. The data is fictional."

## 2 — Show site drilldown

In Dashboard, switch between All regions, Germany and France. Call out the inventory accuracy and punctuality definitions. Explain why a shared data model improves reporting consistency. Click an individual store row and point to the active exception count.

## 3 — Show quality checks

Open `retailops/data_quality.py`. Explain validation for missing IDs, negative quantities, unknown foreign keys and malformed dates. Mention transactional imports and idempotent primary keys. Show the `tests/test_validation.py` checks.

## 4 — Demonstrate human review

Open Issue review. Choose an OPEN issue and read its rule-derived source evidence. Show the status transition options. In API docs, explain why OPEN → RESOLVED is rejected. Then submit a legitimate OPEN → IN_REVIEW transition with a note, followed by resolution. Open the audit history.

## 5 — Explain optional AI

Show deterministic insight first. Emphasize that anomaly detection is not performed by the LLM. Optional LLM summaries are requested only when a reviewer clicks the button, and the model cannot approve or change an issue. Do not call the paid endpoint without an approved API key and spending policy.

## 6 — Google Workspace extension

Open `automation/Code.gs`. Point to functions for updating Sheets and sending authorized daily summaries. Explain that Google Apps Script requires a reachable HTTPS backend and explicit authorization. Do not pretend the Google integration is live unless actually configured and tested.

## 7 — Close with engineering tradeoffs

Highlight metrics documentation, FastAPI endpoints, optional dbt analytical views, tests, security gaps and the roadmap to production (OIDC, PostgreSQL integration tests, incremental updates, OpenTelemetry).

## Suggested user acceptance tests

- Can a manager identify the highest-issue store within 15 seconds?
- Does changing region change all KPI cards and the drilldown consistently?
- Can a reviewer record evidence and see the corresponding audit history?
- Are empty regions, failed API requests and missing LLM keys understandable?
- Can a business analyst use the metric definitions to reconcile dashboard numbers?

Collect findings in a feedback sheet and prioritize by end-user impact.
