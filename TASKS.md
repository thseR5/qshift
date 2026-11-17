# Build checklist

- [x] Inspect workspace and referenced execution brief; confirm fresh project.
- [x] Write baseline architecture and safety documents.
- [x] Implement tenant-aware database models and fictional demo seed.
- [x] Implement deterministic paise pricing, imports, change proposals, catalogue choice and approvals.
- [x] Implement PDF output, memory, version history and simulated interface.
- [x] Add transcript fixture and multilingual normalization entry point.
- [x] Run unit, workflow, property, API, lint, evaluation and demo checks; verify results below.
- [x] Document Phase 3–6 roadmap, Meta verification boundary, pilot methodology and limitations.
- [x] Add Colab notebook and reproducible 3-minute demo instructions.

Colab notebook: created but not executed in Colab; marked unverified.

## Verification record (2026-11-09)

- `make setup`: passed using the project-local Python 3.11 virtual environment.
- `make test`: 18 passed; engine/approval combined coverage 94%. One Starlette `TestClient` deprecation warning.
- `make lint`: Ruff and strict mypy passed.
- `make eval`: 180 synthetic cases; P/R/F1 and line/target exact-match were 1.00 for each fixture language. This is curated mock-fixture performance only.
- `make clean-demo && make migrate && make demo`: passed; repeated `make demo` reset also passed. PDF created at `demo-output/sharma-residence-quote-v2.pdf`.
- `make eval-live`: correctly reports no live model adapter configured.
- PostgreSQL service tests and Colab notebook execution remain unverified.

# V6 execution tasks

## In progress

- [x] Read V6 specification and prior founder audit.
- [x] Run baseline test, lint, evaluation, secret scan and full type-check commands.
- [x] Record the audit in `docs/QSHIFT_FOUNDER_AUDIT.md`.
- [x] Create release gates and known-limitations documents.
- [ ] Establish the first Git baseline commit after reviewing the staged file list.
- [ ] Add import mapping preview and explicit alias handling for safe supported CSV/XLSX onboarding.
- [ ] Add conversational cancellation and explicit draft/version ambiguity handling.
- [ ] Add regression tests for the new onboarding and conversation states.

## P0 safety invariants

- [ ] Every new business read/write remains scoped by `firm_id`.
- [ ] No uploaded file or message can authorize a price, approval or tool action.
- [ ] Unsupported or ambiguous work becomes manual review or clarification.
- [ ] Existing approval, immutable-version, tenant-isolation and money tests remain green.
- [ ] No real data, secrets, live messages, public deployment or billing activation.

## Later, gated work

- [ ] Real-model holdout evaluation.
- [ ] Production identity, invitations, recovery and document access.
- [ ] Real-firm import fixtures and founder-assisted pilot.
- [ ] Stable hosting, restore drill and monitoring.
- [ ] Official Meta production eligibility and onboarding.
- [ ] Usage ledger and manual billing records.

