# Qshift architecture (Phase 0–2 prototype)

```mermaid
flowchart LR
  D[Designer in simulated chat] --> API[FastAPI endpoints]
  API --> AUTH[Bearer demo identity + firm scope]
  AUTH --> S[Workflow services]
  S --> L[MockLLM: bounded extraction]
  S --> C[Verified catalogue]
  S --> E[Decimal / integer-paise engine]
  S --> A[Human approval and audit]
  A --> V[Immutable quote version]
  V --> PDF[ReportLab PDF]
  S --> DB[(SQLite demo / PostgreSQL URL target)]
  DB --> M[Stored project memory and history]
  S --> T[Mock transcript fixture]
```

The model adapter proposes typed operations. Services validate every target and rate, apply only verified catalogue records, recompute with deterministic code, and produce a draft bound to its base version and content digest. The approval service checks the authenticated role, exact content hash, expiry, current quote base and current rate-card reference before appending an approved version. PDF rendering uses the persisted approved version. Project memory reads stored operations and versions only.

Every persistent business row has `firm_id` and every service query includes it. The browser demo bearer tokens represent fictional users and are not production authentication. SQLite is exercised locally. PostgreSQL deployment and concurrency behavior have not been validated in this run.

