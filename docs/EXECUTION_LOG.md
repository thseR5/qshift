# Qshift V6 execution log

This log records local engineering evidence. It does not authorize spending, DNS changes, public deployment, live WhatsApp messaging, payment collection or real-customer data.

## 2026-11-17 — baseline and audit

Scope: repository inventory, secret scan, tests, lint, evaluation and full type-check.

Commands and results:

```text
git branch --show-current
master

git log -1 --oneline --decorate
fatal: your current branch 'master' does not have any commits yet

python3 --version
Python 3.11.15

make test
40 passed, 1 warning in 5.40s
Coverage target qshift.engine + qshift.approval: 94%

make lint
Ruff passed
mypy qshift/engine qshift/approval passed

make eval
180 deterministic synthetic fixture cases; all printed fixture scores 1.000

make eval-live
No live LLM adapter is configured in this offline scope.

.venv/bin/python -m mypy qshift
82 errors in 13 files
```

Secret scan found no credential values or private keys in repository text. Development defaults and synthetic test secrets remain in source by design and must never be accepted outside development. `.gitignore` excludes `.env`, databases, `work/`, caches and generated outputs.

Evidence: `docs/QSHIFT_FOUNDER_AUDIT.md`.

## 2026-11-17 — external-action boundary

No DNS, registrar, hosting, payment, Meta, email or customer-data action was performed. Official Meta policy was checked for the audit. The current policy requires recipient opt-in, opt-out handling, approved templates for business-initiated messages outside the 24-hour window, clear human escalation and privacy/data controls.

## 2026-11-17 — import usability and cancellation slice

Changed:

- `qshift/services.py` now normalizes safe CSV/XLSX header aliases, supports explicit GST percentage conversion to basis points, and exposes read-only `preview_import` output. Preview does not write the database.
- `qshift/api/main.py` adds authenticated `/api/imports/rate-card/preview` and `/api/imports/quotation/preview` endpoints.
- `qshift/services.py`, `qshift/agent/chat.py` and `qshift/intake.py` support explicit cancellation of open drafts without changing the last approved quote version.
- Added regression tests for alias mapping, GST conversion, preview no-write behavior, service cancellation and API cancellation.

Verification:

```text
make test
44 passed, 1 warning in 5.64s

make lint
Ruff passed
mypy qshift/engine qshift/approval passed
```

Status: local fictional/test data only. The mapping is deterministic and intentionally does not use fuzzy matching or auto-verify any rate.

## 2026-11-17 — truthful public entry point

Changed:

- Added a local-only `/site` marketing entry point with a clear fictional/simulated boundary, pilot CTA and a link into the working demo.
- Added responsive marketing CSS under `qshift/web/marketing.css`; no official logo asset was copied or invented.
- Added API coverage for `/site` and its stylesheet.
- Project change memory now reports cancelled operations explicitly.

Boundary: no DNS, hosting, Meta, WhatsApp or external email action was taken.

## 2026-11-17 — read-only domain check

- `qshift.in` resolved to `192.64.119.99`.
- HTTPS timed out after 10 seconds.
- No DNS, registrar, hosting or certificate change was attempted.
- Evidence is recorded in `docs/DOMAIN_AND_DEPLOYMENT_AUDIT.md`; deployment remains unverified.

## 2026-11-17 — reproducible demo recheck

```text
make demo
Demo complete. No live messaging or external send occurred.
PDF generated: demo-output/sharma-residence-quote-v2.pdf
```

## 2026-11-17 — real-customer-intelligence implementation slice

Changed:

- Added `ChangeExtraction`, validated operation schemas and provider selection in `qshift/agent/extraction.py`.
- Added an explicit Ollama adapter using `QSHIFT_CHANGE_MODEL_PROVIDER=ollama`; its output is untrusted and cannot price, approve or issue documents.
- Replaced the service-layer revision path's direct hard-coded dependency with configurable extraction plus manual-review fallback when the model is unavailable.
- Added deterministic quotation-line/catalogue matching, firm-scoped aliases, ambiguous candidate handling and quantity/dimension modification support.
- Added persistent open-draft amendment handling for corrections without changing approved versions.
- Added migration `0010_rate_entry_aliases` and import persistence for inert aliases.
- Added `qshift/fixtures/revision_eval_v1.json` and `evals/run_live_eval.py`.

Verification:

```text
make test
51 passed, 1 warning; engine/approval coverage remained 94%

make lint
Ruff passed; configured engine/approval mypy passed

make eval-live
LIVE EVAL BLOCKED: Ollama is unavailable at http://127.0.0.1:11434/api/chat
No model was downloaded and no paid provider was contacted.
```

The live-model metrics are intentionally not fabricated. Offline fixture scores remain mock-only evidence.

Full modified-module mypy check was also run with:

```text
.venv/bin/python -m mypy qshift/agent/extraction.py qshift/services.py qshift/models.py qshift/api/main.py
75 errors in 9 files
```

The errors are existing repository-wide typing debt and missing third-party stubs (plus transitive modules imported by the checked files); the configured `make lint` gate remains green for `qshift/engine` and `qshift/approval`.

## Next entry format

```text
Date / task
Files changed
Tests added
Commands and exact result
Real vs mock status
Known limitations
Next safe action
```
