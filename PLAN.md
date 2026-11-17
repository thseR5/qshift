# Implementation plan

## Scope

Implement the offline-first Phase 0–2 and Demo Mode slices from the supplied Qshift execution brief. Live Meta connectivity, client-facing conversations, billing and real customer data stay out of scope.

## Architecture

FastAPI → tenant-scoped SQLAlchemy services → deterministic quotation engine / approval module / fixture-based agent → SQLite by default, PostgreSQL by URL → ReportLab PDF. A static WhatsApp-style simulator calls the same API services. Mock LLM and transcriber work offline.

## Delivery order

1. Phase 0 documents, risk register and architecture.
2. Tenant setup, fictional seed fixtures, rate and quote imports.
3. Money engine, structured change proposals, clarification, human approval, version history and PDF.
4. Simulated chat and project memory.
5. Transcript fixture, normalization and transcript confirmation.
6. Unit/integration/property tests and synthetic evaluation command.
7. Reproducible demo, quickstart, Colab notebook and roadmap.

## Constraints and verification

Use Python 3.11 with the specified FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 and ReportLab stack. SQLite is exercised locally. PostgreSQL compatibility is architectural only until an actual PostgreSQL service is available; no PostgreSQL test result will be claimed.

## V6 execution overlay

Move the existing repository toward the strongest honest first-customer release. Preserve deterministic pricing, tenant scoping and human approval. Do not treat a local tunnel, fake Meta endpoint, model fixture or domain purchase as production proof.

Delivery order:

1. Establish a recoverable Git baseline and truth documents.
2. Make ordinary supported onboarding possible without terminal or database edits.
3. Improve CSV/XLSX mapping, preview, aliases and import provenance.
4. Replace the default narrow revision parser with a provider-agnostic proposal/resolver boundary while retaining deterministic resolution and approval.
5. Add cancellation, explicit version/project ambiguity handling, editable draft review and failure-safe recovery.
6. Harden production-mode authentication, upload handling, document access, secrets and operational checks.
7. Prepare an accurate public website and founder-assisted pilot assets.
8. Re-run real-model evaluations and fictional end-to-end acceptance scenarios.
9. Prepare deployment and DNS instructions only. Do not deploy, change DNS, send live messages or activate billing without separate authorization.

Current release classification: Gate A is substantially present. Gate B is preparable with fictional data. Gates C and D are not passed. See `docs/RELEASE_GATES.md`.

