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

## 2026-11-17 — V6.2 onboarding mapping slice

Changed:

- Added explicit mapping overrides to rate-card and quotation import services and multipart API endpoints.
- Added Studio preview/confirm mapping controls for nonstandard CSV/XLSX headers.
- Added alias and explicit-mapping regression tests; validated browser JavaScript syntax with `node --check`.
- Expanded the live evaluation set to 55 independently written fictional multilingual cases; no model result was fabricated.

Verification:

```text
make test
52 passed, 1 warning; engine/approval coverage remained 94%

make lint
Ruff passed; configured engine/approval mypy passed

node --check qshift/web/studio.js
passed
```

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

## 2026-11-17 — V6.3 local real-model activation

The founder-authorized local-only runtime evaluation was completed on this Mac. No paid
provider, public infrastructure, live WhatsApp send or customer data was used.

Environment checks:

```text
architecture: arm64
macOS: 26.6.2
RAM: 8.0 GB
free storage: 143 GiB
Homebrew: /opt/homebrew/bin/brew, 7.0.11
```

Commands and results:

```text
brew install ollama
Ollama 0.40.16 installed successfully

brew services start ollama
curl http://127.0.0.1:11434/api/tags
{"models":[]}

ollama pull qwen3:1.7b
success; qwen3:1.7b, 1.4 GB, Q4_K_M, model id 8f68893c685c

curl http://127.0.0.1:11434/api/tags
qwen3:1.7b present; inference probe succeeded
```

Implementation changes:

- The Ollama adapter now exposes a small model-only schema. Internal fields such as resolved
  line IDs, catalogue options, prices, totals, status and approval state are not in the model
  schema and are never trusted from the response.
- Raw model JSON and raw response text are saved by the live evaluator; normalized proposals
  remain separate from the evidence record.
- The evaluator supports a held-out slice and reports operation and clarification metrics.
- Quotation import now returns deterministic `unmatched_items` review records with candidate
  verified SKUs; Studio displays those records after import.

Verification:

```text
make test
54 passed, 1 warning; engine/approval coverage 94%

make lint
Ruff passed; configured engine/approval mypy passed

full mypy comparison
218 errors on V6.4 working tree; 219 errors on git baseline b7b59ec
=> one existing evaluator typing error was fixed; no newly introduced full-check errors detected; release-critical configured gates remain green
```

The exact live evaluation evidence is in `work/revision_eval_live_v63.jsonl` and the held-out
slice is in `work/revision_eval_live_v63_heldout.jsonl` (both ignored from git).

Real FastAPI endpoint checks with `QSHIFT_CHANGE_MODEL_PROVIDER=ollama` used separate SQLite
files and only seeded fictional Demo Interiors data:

- Bedroom false-ceiling removal: `DRAFT_READY`; deterministic line resolution verified the
  removal, authorized approver committed version 2 at ₹2,18,000, and the authenticated PDF
  endpoint returned HTTP 200 with an 11,507-byte PDF.
- Kitchen quartz replacement plus ceiling removal: `NEEDS_CLARIFICATION`; the model proposed
  the correct broad pair but deterministic catalogue matching found two verified quartz rates,
  so no approval was possible until a designer selects one.
- Romanized Telugu correction request: `NEEDS_CLARIFICATION`; the model produced a MODIFY draft
  without a valid quantity/dimension, so no quotation version or PDF was issued.

The second and third outcomes demonstrate the safety boundary: uncertain real-model proposals
remain drafts and cannot create approved documents.

## 2026-11-17 — V6.4 forensic scorer and controlled context comparison

Changed:

- Added `evals/forensics.py` with auditable one-to-one operation alignment and separate intent,
  operation-type, target, room, clarification and fully-correct metrics.
- Added `evals/run_forensics.py`, a 55-case table generator that preserves the original strict
  scorer as historical evidence and reports context coverage.
- Added locked v2 development, validation and holdout fixtures under
  `qshift/fixtures/revision_eval_v2/`; the new holdout has not been used for tuning.
- Added bounded generation diagnostics and captured Ollama `done_reason`/token metadata.
- Made minimal model context the service default; full quotation context remains opt-in.
- Added Slurm preparation scripts that refuse submission without explicit authorization and do
  not download models or expose Ollama outside loopback.

Results:

```text
Full-context V6.3 historical strict F1: 0.029; forensic operation-type F1: 0.511; target F1: 0.321
Minimal-context V6.4 strict F1: 0.037; forensic operation-type F1: 0.593; target F1: 0.481
Fully-correct case rate: 0.109 in both runs
Context coverage: 23/55 gold cases had a unique target in the historical three-line context
Controlled num_predict 350 vs 1200: identical six-case operation-type F1 (0.500)
No-context diagnostic: operation-type F1 0.571 on the same six cases
```

Evidence and the full per-case table are in `docs/REVISION_AI_FORENSICS_V64.md`. No university
GPU job was submitted because Slurm authorization and site resource values are not confirmed.
The submission wrapper was safety-checked with `QSHIFT_HPC_AUTHORIZED=false` and refused with
exit code 2 before invoking `sbatch`.
## 2026-11-17 — V7 WhatsApp-native workflow slice

- Bound a WhatsApp enrollment to a tenant-scoped fictional staff user and added a migration for
  `user_id` and `pending_version_id`.
- Reoriented chat commands toward the channel: `projects`, `use`, `status`, `review`, `approve
  <one-time-token>`, `reject`, `history`, `changes` and `cancel`. Interactive list/button metadata
  is returned with text fallbacks; a plain `yes` cannot approve.
- Added `deliver_pending_pdf`, which renders the exact approved immutable version, commits the
  send attempt before transport and records `accepted`, `needs_review` or `suppressed`.
- Added a disabled-by-default Bedrock provider boundary and an AWS account/deployment checklist.
  The account checklist was run; AWS CLI is not installed in this workspace, so no account or
  credit facts were inferred and no AWS resource was created.
- Verification: `make test` — 58 passed, 1 warning. `make lint` — Ruff and configured mypy passed.
- Direct fictional revision smoke flow (enrolled APPROVER -> `review` -> one-time
  `approve <token>` -> pending PDF worker) returned `pdf_state=accepted`, generated 11,572 PDF
  bytes, and verified the `%PDF-` header. No network sender was used.

