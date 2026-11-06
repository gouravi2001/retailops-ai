# Security and edge-case checklist

## Implemented safeguards

- API keys required for issue state changes and viewing the audit history.
- Auth uses constant-time comparison for supplied API keys.
- Pydantic validates mutations and rejects invalid statuses or very short notes.
- Only allowed state transitions are accepted; illegal jumps yield HTTP 409.
- Accepted changes persist an audit event in the same database transaction.
- Pandas and optional Pandera validate input before writing, and store/product foreign keys are checked.
- Uploaded/generated data uses fictional store and transaction records only.
- Optional LLM gets aggregates, never raw customer transactions or secrets.
- Docker-exposed ports bind to local loopback only.

## Known limitations

The demo has no user authentication, no role-based authorization, no rate limiting, no issue ownership, no separation between report readers, and no tamper-evident immutable audit log. The API key is shared across admin-level actions. Published GET reporting endpoints are not protected. Apps Script configurations are only examples and require HTTPS deployment to function. The database demo password is not secure for production. The code is **not** ready for public deployment.

## Edge-case behavior

| Case | Behavior |
|---|---|
| Unknown store/product in CSV | Validation error before DB commit |
| Negative count/price or invalid date | Validation error |
| Duplicate primary key in a CSV | Validation error |
| Import repeated IDs | Upsert replaces matching source rows |
| Repeated anomaly detection | Existing `(kind, source_ref)` issue not duplicated |
| Expected inventory = 0 | Relative accuracy denominator gracefully handled; discrepancy >= 3 flags issue |
| Region with no stores | Empty rows and N/A percentages |
| Pending deliveries | Excluded from punctuality KPI; overdue ones flagged by rules |
| OPEN directly to RESOLVED | HTTP 409 |
| Missing write API key | HTTP 401 (or 503 if server not configured) |
| Missing model API key | HTTP 503 on optional AI endpoint only |
| Third-party AI service failure | HTTP 502 with safe general message |

## Production security backlog

Use OIDC, per-user roles/permissions, approved HTTPS ingress, secrets manager, credential rotation, database least privilege, signed audit events, DB schema migrations, access logs with PII redaction, request rate limits, CSRF protection where applicable, and a periodic third-party vulnerability review. Add privacy and governance review before external LLM usage with real company data.
