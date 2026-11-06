# Architecture and technical decisions

## Data flow

The generator produces five CSVs with fictional records. `retailops.data_quality` checks exact schema, types, value ranges, uniqueness and cross-table references. `retailops.ingest` writes all source data through a single SQLAlchemy transaction; PostgreSQL is used in Docker and SQLite is provided for easy local experimentation.

`retailops.anomalies.build_issues()` creates an idempotent exception record for each rule violation, uniquely keyed by `(kind, source_ref)`. Operational analytics produce KPIs from structured records. FastAPI serves both analytical reads and controlled state mutations. Streamlit consumes HTTP APIs, rather than accessing the database directly.

Google Apps Script is a separately configured cloud integration: it is not a local-to-remote bridge and cannot access `localhost`. The LLM is another optional integration which only receives aggregated synthetic records and cannot take business actions.

## Data ownership boundaries

- `stores`, `products`, `sales`, `inventory`, `deliveries`: imported data tables.
- `issues`: system-generated exception state; humans manage statuses.
- `audit_events`: traceability of successful status changes.
- Dashboard: presentation, not database truth.
- Optional LLM: advisory narrative, not authoritative data source.

## Decision rationale

| Choice | Reason | Tradeoff |
|---|---|---|
| PostgreSQL | Familiar relational constraints, SQL transformations and analytics | Requires deployment/operations |
| SQLite local | Instant start, isolated tests | Not suitable for production concurrency |
| Deterministic anomaly rules | Auditable and cheap | Needs policy tuning |
| Human-only resolution | Prevents speculative automated closure | Operational workload remains |
| FastAPI REST | Clear separation of backend and UI | Needs proper production auth |
| Streamlit / Plotly | Fast prototype and strong analytics demo | Less customizable than a dedicated frontend |
| Apps Script | Practical Workspace/reporting integration | Google service quotas and auth setup |
| Optional dbt | Reusable, tested SQL views | Not used by API until explicitly integrated |
| One explicit LLM request | Controls cost and avoids constant AI calls | Narrative availability depends on external service |

## Extension points

Replace synthetic CSVs with approved company sources. Add ingestion watermarks and upsert keys, data lineage, a scheduler and a real data quality quarantine path. Move metrics into documented SQL/dbt marts. Add proper organization auth, roles, audit retention and release versioning. Introduce Prometheus/OpenTelemetry instrumentation for production incidents.
