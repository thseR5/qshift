# QSHIFT — Founder and Engineering Audit

Audit mode: read-only diagnostic. No application code, database, secret, deployment, payment setting, or Meta configuration was changed for this report. Additional local checks used only fictional text and in-memory data.

Audit date: 2026-11-17 (Asia/Kolkata)

## 1. Executive verdict

QShift is a **functioning offline prototype with a narrowly controlled pilot adapter**, not a production-ready SaaS and not a commercially validated startup.

What is real in the repository:

- A FastAPI application with SQLAlchemy models and Alembic migrations.
- A local simulated client/WhatsApp browser flow that can create a first quote, ask for a missing dimension, calculate a deterministic total, require a role-authorized approval, generate a PDF, and retrieve the PDF only inside the originating simulated chat.
- A separate staff-pilot adapter that validates Meta-shaped webhook signatures, scopes one enrolled sender, deduplicates message IDs, stores a 24-hour consent window, and contains real Meta Cloud API text/PDF request code behind environment switches.
- A local Ollama adapter for `qwen3:1.7b`, with strict schema and evidence validation, but only for a small wardrobe/two-item intake.
- Deterministic integer-paise pricing, rate verification, immutable quote versions, and approval replay/staleness checks.

What is not proven:

- No repository evidence proves a successful live Meta request. The tests use a fake Meta endpoint, and `docs/PILOT_TEST.md` explicitly says no live pilot has been run. A prior manual browser session is not a reproducible repository artifact, so the live result is **NOT VERIFIED** by this audit.
- No real customer or interior-design-firm usage, quote comparison, payment, retention review, or measured commercial demand is present in the provided project materials.
- No production authentication, tenant provisioning workflow, billing, monitoring, backup restore, audio processing, PDF/image/OCR quotation import, or broad multilingual evaluation exists.
- PostgreSQL compatibility is an architectural target, not a current production reliability claim.

The biggest reason results can disappoint is not the arithmetic. It is the narrow intelligence and product boundary. The revision path is a hard-coded pattern adapter for a few countertop/ceiling phrases, and the first-quote path is constrained to one wardrobe or one gypsum-ceiling sample. The repository has excellent guardrails around those supported examples, but those guardrails do not create general interior-design understanding.

Current repository evidence also corrects the earlier status report. `make test` currently collects **40 tests and passes all 40**, not 38. `make lint` passes its narrow Ruff and mypy target. A full `mypy qshift` run reports **82 errors**. Coverage is only measured for `qshift.engine` and `qshift.approval`, at 94% combined, not for the application as a whole.

## 2. Verified feature inventory

| Feature | Implementation files | Current status | Verification evidence | Known limitations |
|---|---|---|---|---|
| Authentication and user identity | `qshift/api/main.py`, `qshift/studio_auth.py`, `qshift/models.py` | Implemented in two demo modes | `tests/test_api.py::test_simulated_api_auth_and_scope`; `tests/test_studio.py::test_studio_accounts_control_projects_rates_and_approvals` | Legacy mode uses seeded bearer tokens. Studio accounts are operator-provisioned. No MFA, recovery, email verification, or production identity provider. |
| Firm registration | `qshift/studio_auth.py::provision` | Local operator provisioning only | `tests/test_studio.py` provisions fictional Maple and Cedar firms | No self-service signup, business verification, invite workflow, or customer onboarding UI. |
| Multi-tenant isolation | `qshift/services.py`, `qshift/api/main.py`, model `firm_id` columns | Implemented for tested service/API paths | `tests/test_workflow.py::test_cross_tenant_project_access_is_denied`; studio cross-firm checks | Not stress-tested on PostgreSQL. Some demo seed/admin paths are intentionally special-cased. |
| Project creation and selection | `qshift/services.py::create_project`, `pin_project`, `qshift/agent/chat.py` | Implemented | API and studio tests; local chat commands `projects` and `use <id>` | Project context is selected manually. The live pilot is bound to one seeded fictional designer and one enrollment. |
| Rate-card upload | `qshift/services.py::import_rate_card` | Implemented for CSV/XLSX | `tests/test_imports.py::test_imported_rate_is_unverified_until_approver_confirms` | Fixed header schema. No spreadsheet formula quarantine, virus scan, validation workbook, or alias normalization. |
| Rate verification | `qshift/services.py::verify_rate` | Implemented | Import test and studio test | Verification is a per-row role action. No maker-checker policy, provenance UI, effective dates, or rate approval history beyond audit events. |
| Quotation upload | `qshift/services.py::import_quotation` | Implemented for simple CSV/XLSX | `tests/test_imports.py` | Requires exact `room,sku,quantity` and an already verified SKU. |
| Original quotation parsing | `qshift/services.py::import_quotation` | Limited tabular parser only | Same import test | PDF, scanned PDF, image, OCR, ERP export, merged cells, discounts, package lines and free text are **NOT IMPLEMENTED**. |
| Scope-change extraction | `qshift/agent/extraction.py::MockLLM`, `qshift/services.py::submit_change` | Implemented only for deterministic patterns | `tests/test_extraction.py`, `tests/test_whatsapp_rehearsal.py` | Hard-coded quartz/granite/countertop and false-ceiling patterns. It is not a general LLM revision agent. |
| First-quote extraction | `qshift/agent/local_model.py`, `qshift/agent/itemized.py`, `qshift/intake.py` | Implemented for narrow local Qwen samples and deterministic fallback | `tests/test_local_model.py`, API/studio tests with monkeypatched Ollama | Local-only model endpoint. Supported fields and item catalogue are intentionally narrow. |
| Clarification | `qshift/intake.py`, `qshift/agent/chat.py` | Implemented for one missing field at a time and catalogue choice | `tests/test_api.py::test_chat_clarifies_prices_and_keeps_approval_in_review`; intake flow | No robust multi-uncertainty dialogue manager. Revision clarification is mostly “choose verified SKU” or generic target clarification. |
| Pricing calculations | `qshift/engine/pricing.py` | Implemented deterministically | Six pricing tests, including half-up rounding, GST slabs, idempotence and property-style totals | No discounts, dependency graph, labor rules, package pricing, historical effective rates, minimum charges, or firm-specific formulas. |
| Human approval | `qshift/services.py::issue_approval_token`, `approve_draft`, `qshift/approval/core.py` | Implemented for demo/studio workflow | `tests/test_approval.py`, workflow tests | Cryptographic binding is present. Production identity, MFA, authorization administration and approval notifications are absent. |
| PDF generation | `qshift/services.py::render_pdf` | Implemented with ReportLab | API/workflow tests assert `%PDF-`; generated demo PDF exists | Layout is basic. PDF visual QA is not automated. It is a quotation, not a tax invoice. |
| Project memory | `qshift/services.py::project_memory` | Implemented as a seven-day operation summary | API endpoint and README description | Counts stored draft operations only. It does not answer semantic historical questions or cover all project artifacts. |
| Simulated WhatsApp | `qshift/simulated_whatsapp.py`, `qshift/web/intake.*` | Working local simulator | `tests/test_whatsapp_rehearsal.py`, `tests/test_api.py`, `qshift/simulated_client_demo.py` | Clearly marked simulated. It uses fictional IDs and local auth. It is not a substitute for live Meta behavior. |
| Real Meta test-number messaging | `qshift/whatsapp_webhook.py`, `qshift/whatsapp_delivery.py`, `qshift/whatsapp_pilot.py` | Code path implemented; live result **NOT VERIFIED** in repository | Fake Meta tests exercise the protocol. `docs/PILOT_TEST.md` says no live pilot has been run | One configured sender, text-only inbound, temporary tunnel assumptions, separate worker, no production onboarding. |
| Multilingual text | `qshift/agent/extraction.py`, local-model prompts, fixtures | Synthetic fixture support only | `make eval` reports 180 deterministic fixture cases across labels | No real language benchmark. The deterministic adapter recognizes a tiny marker set. |
| Voice-note handling | `MockTranscriber`, `/api/transcripts/{fixture_name}`, UI button | Mock transcript fixture only | `tests/test_extraction.py::test_voice_fixture_requires_confirmation` | Real audio download, decoding, speech provider, voice media webhook and WER are **NOT IMPLEMENTED**. |
| Error recovery | Pilot durable inbox and retry code | Partially implemented | `tests/test_whatsapp_pilot.py::test_reply_worker_recovers_from_sqlite_busy`, durable inbox and opt-out tests | Uncertain external send is deliberately not retried. No full operational incident handling or alerting. |
| Billing | `/api/pricing` only | **NOT IMPLEMENTED** | `tests/test_api.py::test_founding_subscription_prices` checks constants | No checkout, invoices, GST invoice logic, entitlements, usage counters, collection or cancellation. |
| Deployment | `Dockerfile`, `compose.yaml`, `deploy/*`, `docs/HOSTING.md` | Configuration and runbook exist | Static inspection only | No deployed environment, restore drill, uptime evidence, managed secrets, monitoring, or production acceptance test. |

## 3. Actual architecture

### Repository and working tree

- Root: `/Users/eswarreddytadi/Documents/Codex/2026-11-09/referenced-chatgpt-conversation-this-is-an`
- Branch: `master`
- Latest commit: **NONE**. `git log -1` fails because the repository has no commits.
- Working tree: all project source and documentation files are untracked (`git status --short` shows `??` for the project files). Ignored runtime artifacts include `.venv`, caches, databases, `work/`, `outputs/`, and `demo-output/`.
- Python: `Python 3.11.15` inside the existing environment.

### Relevant source tree

```text
qshift/
  api/main.py                 FastAPI routes, auth modes, imports, approval/PDF endpoints
  db.py                       SQLAlchemy engine/session, SQLite foreign keys
  models.py                   tenant-scoped persistent models
  services.py                 seed data, imports, revisions, approvals, PDF, project memory
  intake.py                   first-quote intake and simulated client delivery
  agent/
    extraction.py             deterministic MockLLM and MockTranscriber
    local_model.py            local Ollama qwen3:1.7b adapter and evidence validation
    itemized.py               two-item local-model sample
    chat.py                   text command/revision conversation handler
  engine/pricing.py           Decimal/integer-paise pricing and GST
  approval/core.py            signed approval token creation/validation
  simulated_whatsapp.py       provider-shaped local webhook and PDF delivery
  whatsapp_webhook.py         Meta-shaped webhook verification and filtering
  whatsapp_pilot.py           one-enrollment staff pilot state machine
  whatsapp_store.py           pilot conversations and receipts
  whatsapp_delivery.py        optional Meta text/media delivery worker
  studio_auth.py              operator-provisioned studio accounts and sessions
  studio_server.py            loopback studio launcher
  web/                        clearly simulated browser interfaces
  fixtures/                   fictional rate cards, extraction cases, templates
tests/                        40 pytest tests
evals/run_eval.py             synthetic deterministic extraction evaluator
alembic/versions/             migrations 0001 through 0009
deploy/                       example environment files and Caddy config
Dockerfile, compose.yaml      containerized hosting target
Makefile                     setup, run, test, lint, eval and demo commands
docs/                         architecture, risks, hosting and pilot instructions
```

### Dependencies and entry points

`pyproject.toml` declares Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic, ReportLab, openpyxl, multipart upload support, dotenv, psycopg, pytest, coverage, Hypothesis, HTTPX, Ruff and mypy.

Main entry points are:

- `make run` → `uvicorn qshift.api.main:app --reload`.
- `make studio` → `qshift.studio_server`, loopback port 8079, signed-in studio mode.
- `make client-demo` → simulated WhatsApp rehearsal against a running app.
- `make webhook-demo` → in-process synthetic webhook rehearsal.
- `make run-whatsapp-pilot` → separate receive-only pilot service.
- `make whatsapp-test` → script for the authorized local/test-number procedure.
- `python -m qshift.whatsapp_delivery` → separate optional text/PDF delivery worker.

SQLite is the tested default from `qshift/db.py`. A PostgreSQL SQLAlchemy URL is accepted, and migrations contain PostgreSQL branches, but `docs/ARCHITECTURE.md` says PostgreSQL deployment and concurrency behavior have not been validated in this run.

### End-to-end execution path

1. The browser sends a simulated message to `/api/simulated-intakes/{project_id}/messages` or a provider-shaped event to `/api/simulated-whatsapp/webhook`.
2. `qshift.api.main.current_user` authenticates either a fixed fictional bearer token or a studio cookie.
3. `qshift.intake.add_client_message` stores the conversation, selects deterministic extraction or the local Ollama adapter based on `QSHIFT_INTAKE_MODEL`, and asks one missing-field question at a time.
4. The extracted facts are validated against client evidence. The service selects only a verified rate entry, then `qshift.engine.pricing` computes integer-paise totals.
5. A `Draft` stores lines, operations, base version, rate-card ID, total and a canonical SHA-256 content hash.
6. An owner/approver requests a token. `qshift.approval.core` binds it to draft, content hash, approver and expiry. `approve_draft` rechecks role, token, replay state, current quote version, current rate, unit, GST and recalculated total.
7. The service appends a new `QuoteVersion`, marks the draft approved, writes an audit event and renders a PDF. In simulated chat, the PDF bytes and hash are stored in `SimulatedQuoteDelivery`.
8. The separate live-pilot path receives signed text, binds it to one configured enrollment, queues or captures a reply, and a worker can call Meta's `/messages` or `/media` endpoints if explicitly enabled.

The product is integrated for the supported simulator flow. The live adapter is a separate, narrower integration and does not provide a generalized multi-firm WhatsApp product.

## 4. Real user journey

### Existing first-quote browser journey

The actual local flow is:

1. Start the local FastAPI app and use a fictional demo token, or provision a local studio account.
2. Open `/intake`, choose the wardrobe or two-item sample, and start a fictional project.
3. Send a message such as “wardrobe for guest bedroom, white laminate, 6 ft wide”.
4. QShift asks the missing height question.
5. Send “7 feet”. The system calculates `6 × 7 = 42 sqft`, at the fictional rate ₹1,250/sqft, for ₹52,500.
6. Review the line and hash in the browser. A designer cannot approve.
7. Switch to owner/approver, request an approval token, and commit the approval.
8. Download the generated v1 PDF from the simulated delivery bubble.

The two-item sample is a separate Ollama-only flow for one wardrobe plus one gypsum ceiling. It is not evidence of general item coverage.

### Existing revision journey

1. Send `projects` in the text simulator.
2. Send `use <project ID>`.
3. Send a supported revision, such as a quartz replacement and/or bedroom false-ceiling removal.
4. If quartz is requested, choose an exact verified SKU.
5. Review in the browser. Approval is not performed by the chat command.
6. Approve in the authenticated review screen and retrieve a new immutable PDF/version.

### Interaction counts

Measured from the code and test flow, not from a customer study:

| Request | User actions in the simulator | Status |
|---|---:|---|
| Complete wardrobe first quote with all facts except height | Start sample, send brief, answer height, switch role, approve, download = about 6 actions | Code-path count, not user research. |
| Revision with no catalogue ambiguity | Select project, send change, switch/review, approve, download = about 5 actions | Code-path estimate based on `tests/test_workflow.py`. |
| Revision requiring catalogue clarification | Select project, send change, send `choose <SKU>`, switch/review, approve, download = about 6 actions | Code-path estimate. |
| Live pilot setup | Start processes, configure callback, consent, test token, messages, terminal review/approval, worker send | Operational count, not an in-product onboarding flow. |

### WhatsApp boundary

Users can send text and receive text replies through the pilot adapter, and the code can upload/send one approved PDF. They cannot complete setup, rate-card import, rate verification, approval, or production onboarding inside WhatsApp. Those require the local browser, a terminal operator, a configured database, and private environment variables.

The simulator and pilot share some revision services but differ materially in identity, first-quote intake, storage and transport. The simulator is explicitly marked `SIMULATED · FICTIONAL DATA`. The live adapter is one configured sender mapped to seeded fictional records.

### Unexpected messages

Safe local probes against `MockLLM` produced these actual results:

| Input | Actual classification/operation | Assessment |
|---|---|---|
| `Hi` | `out_of_scope`; `CLARIFY` with missing `target, scope` | Safe refusal, but not a natural greeting response in the revision engine. |
| `Change the kitchen.` | `out_of_scope`; generic `CLARIFY` | Does not ask which line, operation, material or quantity. |
| `Make it cheaper.` | `out_of_scope`; generic `CLARIFY` | No discount or scope-reduction handling. |
| `Use the previous quote.` | `out_of_scope`; generic `CLARIFY` | No explicit quote/version resolver. |
| `Actually don't change anything.` | `out_of_scope`; generic `CLARIFY` | No cancellation operation in the conversation handler. |
| `Apply the same changes to the other bedroom.` | `out_of_scope`; generic `CLARIFY` | No cross-room propagation. |
| `Approve the last one.` | `approve_or_reject` at classifier level, but chat returns “use the authenticated Qshift review screen” | Correctly does not let WhatsApp text approve. |
| Telugu-English quartz/ceiling request | Two hard-coded operations, one verified remove and one catalogue clarification | Works only because the fixture matches the rule set. |

### Five worst UX problems

1. The supported scope is much narrower than the product promise. Most natural interior-design requests become a generic clarification or out-of-scope response.
2. The user must leave WhatsApp for approval, rate verification, project setup and operational recovery.
3. Project context is fragile. The live enrollment is tied to one seeded fictional firm/designer and has no customer-facing project chooser with robust ambiguity handling.
4. A pending draft blocks a new draft, while cancellation and revision-of-revision semantics are not conversationally complete.
5. There is no production-quality failure experience. A local model outage, expired window, uncertain Meta send, or temporary tunnel failure becomes an operator task rather than a guided recovery.

## 5. AI performance audit

### Which model is used

There are two different subsystems:

- Revision path: `qshift.agent.extraction.MockLLM`, a deterministic pattern matcher. It does not call an LLM.
- First-quote path: local Ollama HTTP call to `http://127.0.0.1:11434/api/chat`, fixed model `qwen3:1.7b`, `temperature=0`, `num_ctx=4096`, `num_predict=900`, JSON-schema output, 40-second timeout, and Pydantic validation in `qshift.agent.local_model.run_scope_model`.

The switch is `QSHIFT_INTAKE_MODEL=ollama` in `qshift/intake.py`. The documented `QSHIFT_LLM_PROVIDER` environment variable is not used by the application. Fallback behavior is not automatic model substitution. A local failure raises `LocalModelUnavailable` and the caller returns an error or leaves a durable inbox message queued.

### Actual extraction pipeline

1. The app stores numbered client and assistant messages.
2. The local adapter sends a system prompt plus JSON schema and a JSON transcript to Ollama.
3. The model proposes typed `Fact` objects with value, source number and exact evidence substring.
4. `client_source` ensures evidence belongs to a client message and repairs a unique source citation if possible.
5. `validate_fact` checks allowed item/finish, room evidence, dimension bounds, units and pending-question context.
6. Only validated facts become a brief. Missing fields drive the next fixed clarification question.
7. The service selects a verified catalogue entry and computes the price. The model never chooses the price or approval.

For revisions, `MockLLM.classify` and `MockLLM.extract` recognize a few spelling substitutions and keywords. `services.submit_change` then resolves concrete lines and catalogue options deterministically.

### Messy-language evaluation

`evals/run_eval.py` reads 180 hand-authored fixture cases from `qshift/fixtures/extraction_cases.json`, including labels named English, Hindi Devanagari, Hindi Latin, Telugu Latin, Telugu script and noisy transcript. The evaluator executes `MockLLM`, not Qwen, and prints 1.000 scores for every label.

Those scores are deterministic fixture-pattern scores, not language understanding metrics. There are 20 prompt-injection fixtures in `qshift/fixtures/prompt_injection_cases.json`, but `make eval` does not report a security metric for them.

Representative actual probe results are shown in the user-journey table above. The hard-coded adapter does not understand corrections, discounts, arbitrary rooms, item dependencies, or unrelated conversation. The local Qwen path has two tests for evidence citation and measurement context, but no live run is required by the test suite.

### Metrics

| Metric | Result |
|---|---|
| Fixture count | 180 synthetic labeled messages |
| Fixture type | Hand-authored synthetic patterns, not customer transcripts |
| Prompt-injection cases | 20 fixture records; no aggregate safety metric emitted |
| Mock operation precision/recall/F1 | 1.000/1.000/1.000 per printed fixture label |
| Mock line/target exactness | 1.000 per printed fixture label |
| Mock clarification precision/recall | 1.000 per printed fixture label |
| Real Qwen accuracy | **NOT MEASURED** |
| Catalogue matching accuracy | **NOT MEASURED** |
| Wrong-item rate | **NOT MEASURED** |
| Missing-change rate | **NOT MEASURED** |
| Unsupported-change rate on real inputs | **NOT MEASURED** |
| Hindi/Telugu audio accuracy | **NOT MEASURED** |

### Hallucination and guessing risk

Protections exist, but only inside the narrow workflow:

- The local prompt says to extract explicit facts only, cite source evidence, return null for uncertainty, and forbid price/approval fields.
- Pydantic uses `extra="forbid"` for local scope schemas.
- Fact validators require evidence substrings and bounded dimensions.
- Services use only verified catalogue rows and deterministic pricing.
- Approval rechecks line/rate/hash/version state.

Limitations:

- `MockLLM` hard-codes `Bedroom` for ceiling removal and `Kitchen` for countertop replacement. A different room in a natural message can be misattributed or become generic clarification.
- The revision adapter searches `RateEntry.name.ilike("%quartz%")`, not a semantic catalogue or alias map.
- There is no calibrated confidence threshold, evaluator, human correction capture, or model drift monitor.
- A message can be parsed as a generic clarification rather than explicitly marked unsupported or cancelled.
- The product does not currently detect every contradiction or propagate a correction across an existing approved quote.

The biggest AI limitation is **coverage and evaluation**, not output formatting. The system is safe for its fixtures because it declines most unsupported work. That same behavior makes it unsuitable to claim general interior-design automation.

## 6. Pricing and quotation audit

### Supported quotation formats

- Rate cards: CSV and XLSX/XLSM with exact headers such as `sku,name,category,unit,rate_paise,gst_bps`.
- Original quotations: CSV and XLSX/XLSM with exact `room,sku,quantity` rows and verified SKUs.
- Native PDFs, scanned PDFs, images, OCR, photos and ERP exports: **NOT IMPLEMENTED**.
- Manual quotation entry: indirect only through the seeded/sample or API-created project workflow. There is no general line-item editor for arbitrary catalogs.

### Firm-specific structures and matching

The importer lowercases header names, accepts only a fixed set of units, and stores rows as unverified until an owner/approver confirms them. It does not normalize vendor-specific column names, aliases, units, material variants, room taxonomies, discount columns, package lines or historical effective dates. Quotation matching is exact SKU equality within the latest verified card. There is no fuzzy matching or human-assisted match queue.

### Pricing rules that work

`qshift/engine/pricing.py` uses `Decimal`, integer paise and `ROUND_HALF_UP`. GST is grouped by basis-point slab and rounded once per slab subtotal. Tests cover grouping/formatting, half-up rounding, GST, quote-total identity and idempotent recalculation.

Unsupported or unverified scenarios include:

- Item-level or overall discounts.
- Labor/installation dependency formulas.
- Package pricing or minimum charges.
- Quantity conversions between units.
- Partial room removal beyond the hard-coded false-ceiling operation.
- Rate effective dates and historical quote replay against a changing catalogue.
- General tax rules beyond stored GST basis points.
- Currency other than INR.

### ₹52,500 wardrobe example

The repository-supported fictional example is:

```text
Original quotation: none; this is a first-quote intake.
Client messages: wardrobe for guest bedroom; white laminate; 6 ft wide; reply 7 feet.
Parsed facts: item=Wardrobe, room=Guest Bedroom, finish=White laminate,
              width=6 ft, height=7 ft.
Verified rate: fictional WARDROBE-WHITE-LAMINATE, ₹1,250/sqft, GST 0 bps.
Quantity: 6 × 7 = 42 sqft.
Line total: 42 × ₹1,250 = ₹52,500.
Draft: DRAFT_READY, base_version=0, canonical content hash stored.
Approval: server token bound to draft, approver, hash and expiry.
Version: approved v1 appended; prior versions are not edited.
PDF: ReportLab PDF with quotation disclaimer.
Delivery: simulated PDF bytes are stored and hash-checked per chat.
```

This proves the deterministic first-quote fixture, approval binding and PDF generation. It does not prove general item extraction, real customer data handling, real Meta delivery, tax correctness for a live firm, or commercial usefulness.

## 7. WhatsApp integration audit

### Current implementation

`qshift.whatsapp_webhook` implements:

- Meta-style GET callback verification with a separate verify token.
- HMAC-SHA256 comparison of `X-Hub-Signature-256` against the app secret.
- One-megabyte request limit.
- Pydantic validation of WhatsApp-shaped text payloads.
- Filtering by configured account ID, phone-number ID and enrolled sender ID.
- Provider timestamp parsing and a maximum 4,000-character inbound text.

`qshift.whatsapp_delivery` implements official Graph API-shaped calls to:

- `/<version>/<phone_number_id>/messages` for text.
- `/<version>/<phone_number_id>/media` for PDF upload, followed by a document message.

Sending is disabled unless `QSHIFT_WHATSAPP_SEND_ENABLED=true` and a private token/Graph version pass validation. The receive pilot also requires explicit enablement and a separate database. A worker processes receipts outside the webhook request.

### What was actually verified

Repository tests verify a fake Meta endpoint, not Meta itself:

- `tests/test_whatsapp_rehearsal.py` verifies callback challenge, signature rejection, sender/account filtering and replay handling.
- `tests/test_whatsapp_pilot.py::test_two_way_pilot_against_fake_meta_endpoint` verifies fake two-way text flow.
- `tests/test_whatsapp_pilot.py::test_first_quote_pilot_requires_exact_approval_and_sends_one_pdf` verifies fake `/media` and `/messages` calls, exact approval hash, one-attempt behavior and PDF payload shape.

The test does **not** verify multiple-turn live Meta clarification, real media delivery, delivery acknowledgments, out-of-order live events, account review, business verification, number registration, template approval, app review, account coexistence, or production permissions. `docs/PILOT_TEST.md` explicitly says “No live pilot has been run.”

### Duplicate, late and out-of-order messages

- Duplicate message IDs are hashed and ignored by `Receipt` primary keys.
- The durable inbox orders queued events by source timestamp, creation time and message hash.
- Messages outside the recorded 24-hour consent window are skipped or suppressed.
- An uncertain external send is marked `needs_review` and not automatically retried, preventing duplicate customer documents but requiring an operator.
- One pilot enrollment has one conversation/project binding. It is not a general multi-project conversation router.

### Current Meta restrictions relevant to QShift

Meta's current Business Messaging Policy says businesses need recipient opt-in, must honor opt-out requests, may only initiate conversations with approved templates, and may reply without a template inside the 24-hour customer-service window. Automated responses are allowed in that window, but a prompt, clear and direct human escalation path is required. The policy also requires necessary notices, consents, a published privacy policy, and protection against sharing one customer's chat data with another. See the [current WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/) and [Meta's WhatsApp Business Platform overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview/).

The repository's pilot guardrails address some of these points for a fictional one-person test. They do not establish production eligibility for an AI-first commercial SaaS. The current Meta docs expose separate onboarding, permissions, templates, media, audio, partner, embedded-signup, coexistence and app-review tracks. A real-firm product must choose and implement the applicable onboarding model.

### What blocks a real firm's number today

- No production eligibility or app-review evidence for this exact workflow.
- No business-customer onboarding or embedded signup.
- No per-firm Meta asset/phone-number/token model.
- No production webhook hosting and secret rotation evidence.
- No production authentication, support escalation, privacy policy and retention workflow.
- No message-template lifecycle or 24-hour-window operations beyond one pilot.
- No live delivery/receipt monitoring or reconciliation.
- No safe handling of real customer documents and personal data.

## 8. Security and reliability audit

### Approval security

`issue_approval_token` requires OWNER or APPROVER, stores only a token hash, and binds the token to draft ID, content hash, approver ID and expiry. `approve_draft` rejects missing, expired, replayed, cross-approver, cross-draft and tampered tokens. It recomputes the canonical hash and total, verifies the quote base version and rate-card ID, rechecks every verified rate/unit/GST, conditionally claims the draft, marks the token used, and appends a new version.

Evidence: `tests/test_approval.py`, `tests/test_workflow.py::test_designer_cannot_issue_approval`, `test_rate_snapshot_is_rechecked_at_approval`, and `test_full_workflow_approval_pdf_and_immutable_version`.

### Tenant isolation

Service queries generally include `firm_id`, models carry tenant columns, and API PDF delivery joins through the authenticated firm. Studio tests prove Cedar cannot see Maple projects, rates or PDFs. This is good prototype evidence, not a formal authorization audit or PostgreSQL load test.

### Sensitive information

The repository keeps credentials in environment variables and ignores `.env`, deployment env files, databases and work directories. The webhook code avoids printing raw secrets and limits request size. Studio passwords use `hashlib.scrypt`, server-side sessions, HttpOnly/SameSite cookies, origin checks and temporary lockout.

Major gaps remain:

- Demo bearer tokens are intentionally fixed and documented in README.
- Default approval secret is `local-demo-only-change-me` unless overridden.
- No MFA, production identity provider, account recovery, secret manager, encryption-at-rest design for application fields, object-store policy, deletion workflow, retention enforcement, backup restore test, security monitoring or alerting.
- PDF bytes are stored directly in SQLite for simulated delivery.
- No malware scanning or spreadsheet formula-injection quarantine exists.
- Logs and operational access have not undergone a sensitive-data review.

### Is it safe for identifiable real-customer documents?

**NO.** The repository itself says to use fictional data only. Production authentication, retention, deletion, processor agreements, real document parsing, monitoring and deployment hardening are open. The safe answer is not “yes because the demo passed tests.”

## 9. Testing evidence

### Commands run

```text
make test
40 passed, 1 warning in 5.40s
Coverage target: qshift.engine + qshift.approval = 94% (67 statements, 4 missed)
Warning: StarletteDeprecationWarning about httpx/TestClient

make lint
Ruff: All checks passed
mypy qshift/engine qshift/approval: Success, no issues found in 4 source files

make eval
Offline MockLLM synthetic fixture evaluation: 180 cases
English, Hindi, noisy transcript and Telugu fixture labels all printed P=1.000, R=1.000, F1=1.000

make eval-live
No live LLM adapter is configured in this offline scope.

Full application type-check
.venv/bin/python -m mypy qshift
82 errors in 13 files
```

### All 40 tests

```text
tests/test_api.py
  test_simulated_api_auth_and_scope
  test_founding_subscription_prices
  test_itemized_intake_prices_both_lines_and_edits_only_target
  test_whatsapp_bridge_routes_imported_rates_and_delivers_one_exact_document
  test_first_quote_from_chat_to_approved_pdf
  test_chat_clarifies_prices_and_keeps_approval_in_review
tests/test_approval.py
  test_token_binds_draft_hash_user_and_expiry
  test_tamper_and_expiry_rejected
tests/test_extraction.py
  test_telugu_english_request_creates_remove_and_replacement
  test_voice_fixture_requires_confirmation
  test_unit_normalization
tests/test_imports.py
  test_imported_rate_is_unverified_until_approver_confirms
tests/test_local_model.py
  test_measurement_must_match_client_evidence_and_question
  test_unique_client_evidence_resolves_incorrect_model_citation
tests/test_pricing.py
  test_indian_grouping_and_sign
  test_half_up_to_paise
  test_gst_is_rounded_half_up_and_added_to_quote_total
  test_gst_rounds_once_per_slab_subtotal
  test_quote_total_equals_sum_of_line_totals
  test_recalculation_is_idempotent
tests/test_studio.py
  test_studio_accounts_control_projects_rates_and_approvals
tests/test_whatsapp_pilot.py
  test_pilot_factory_stays_disabled_by_default
  test_pilot_keeps_context_and_deduplicates_across_restart
  test_business_changes_and_receipts_roll_back_together
  test_two_way_pilot_against_fake_meta_endpoint
  test_delivery_requires_recent_timestamp_and_honors_opt_out
  test_uncertain_delivery_is_not_retried
  test_consent_is_required_and_expires
  test_seeded_verified_rates_have_provenance
  test_first_quote_pilot_requires_exact_approval_and_sends_one_pdf
  test_reply_worker_recovers_from_sqlite_busy
  test_durable_inbox_survives_process_restart_and_model_failure
  test_opt_out_discards_unprocessed_inbox_text
tests/test_whatsapp_rehearsal.py
  test_callback_challenge_and_signature
  test_only_enrolled_staff_texts_change_state_and_replays_are_ignored
tests/test_workflow.py
  test_full_workflow_approval_pdf_and_immutable_version
  test_designer_cannot_issue_approval
  test_designer_can_reject_and_history_marks_scope_rejected
  test_rate_snapshot_is_rechecked_at_approval
  test_cross_tenant_project_access_is_denied
```

### Missing automated coverage

- Real Ollama inference across representative messages.
- Real Hindi, Telugu, Hinglish, Romanized Telugu and code-mixed accuracy.
- Real audio download, decoding, transcription and transcription-error confirmation.
- PDF/photo/OCR/ERP imports.
- Spreadsheet security and formula handling.
- Discounts, dependencies, labor, packages, historical rates and tax edge cases.
- PostgreSQL migration, transaction isolation, backup restore and concurrent approval stress.
- Real Meta callbacks, delivery statuses, media, timeouts, retries and account onboarding.
- Session expiry, password reset, MFA, support/admin operations and production secrets.
- Usage metering, quotas, billing, invoices and cancellation.

## 10. Product-market fit gaps

### What real designers would struggle with tomorrow

1. Importing a normal quotation. Most firms will not already have the exact `room,sku,quantity` CSV/XLSX format.
2. Mapping their existing materials and rate-card names. Exact SKUs and no fuzzy matching make onboarding manual.
3. Handling more than the sample wardrobe, gypsum ceiling, countertop and false-ceiling patterns.
4. Making changes across multiple rooms, line items, quantities, discounts, dependencies and tax rules.
5. Reviewing and correcting model output in a polished workflow rather than a developer/demo screen.
6. Connecting their WhatsApp Business account and managing permissions without developer intervention.
7. Trusting retention, privacy, support escalation and recovery for real client documents.
8. Paying and seeing usage limits enforced. The ₹999 plan is displayed but not operational.

### Product differentiation today

The implemented differentiation versus ChatGPT plus Excel is real but narrow:

- Verified rate rows, deterministic calculation and source-linked facts.
- Server-side human approval with exact-content binding.
- Immutable quote versions and a basic change summary.
- Simulated same-chat PDF delivery.

It is not yet a strong general workflow moat. There is no broad document ingestion, firm-specific catalogue intelligence, multi-user operations, live WhatsApp onboarding, or measured reduction in quote turnaround/corrections. Therefore “better than ChatGPT plus Excel” is an explicit hypothesis, not an established result.

### Project memory

`project_memory` is useful as a deterministic audit summary of stored draft operations during the last seven days. It returns requested/included/pending/rejected counts and raw operation records. It does not answer semantic questions, summarize documents, include every conversation artifact, or distinguish a correction from an abandoned request beyond stored status.

### Features to postpone

Postpone image generation, broad voice support, complex AI autonomy, public self-service onboarding, and billing automation until a real studio completes representative quote and revision tasks. First make rate-card ingestion, quote comparison, revision correctness and live support reliable.

## 11. P0 / P1 / P2 prioritized issue register

| Priority | Problem and evidence | Recommended fix | Dependencies | Acceptance criteria |
|---|---|---|---|---|
| P0 | General AI quality is unmeasured. `make eval` only measures `MockLLM` fixtures. | Build a versioned, hand-labeled evaluation set from consented/sanitized firm examples and compare model output to independent designer labels. | Founder access to representative fictional/sanitized quotes; evaluation rubric. | Per-language precision/recall, wrong-item, missing-change and clarification metrics with denominators and stop thresholds. |
| P0 | Live Meta behavior is not reproducibly verified in the repo. Tests use fake endpoints; docs say no live pilot. | Re-run a documented one-tester test only with explicit authorization, record redacted request/response IDs and delivery evidence, then remove test data. | Meta test account, temporary or stable HTTPS, tester consent. | Reproducible receive, multi-turn clarification, approval, PDF delivery, duplicate/late/retry behavior. |
| P0 | Production identity and data safety are absent. README says demo tokens, no MFA, no encrypted storage or hardening. | Add production identity provider, tenant provisioning, secret manager, retention/deletion controls, audit access controls and threat-model review. | Hosting choice, privacy/legal decisions, budget. | No seeded tokens, MFA/recovery, tenant isolation tests, documented deletion and restore drill. |
| P0 | Current scope parser can mis-handle natural instructions. Hard-coded patterns in `MockLLM`. | Replace with a versioned structured extraction service plus deterministic resolver and human correction capture. | Evaluation set and supported catalogue model. | No silent wrong-item or unsupported operation on acceptance suite; ambiguous requests ask targeted questions. |
| P1 | Import requires exact demo schemas and exact SKU. | Add mapping preview, column aliases, units, duplicate/outlier review and firm-specific SKU alias tables. | Sample firm rate cards. | A new firm can import a representative rate card and quotation with zero developer edits and an auditable review. |
| P1 | Revision conversation is incomplete. Cancellation, “make cheaper,” “previous quote,” cross-room propagation and multi-draft context are not supported. | Add explicit intent/state machine with cancel, version selection, target disambiguation and draft lifecycle. | UX decisions and acceptance transcripts. | Each listed unexpected message has a deterministic safe response and no unintended mutation. |
| P1 | Voice is only a fixture. | Add official WhatsApp audio media retrieval, speech provider adapter, transcript confirmation and WER/error logging. | Provider, retention policy, language test set. | Audio fixtures and live test recordings complete end to end with correction capture. |
| P1 | Stable hosting, monitoring and restore are not proven. | Deploy isolated environments with managed secrets, health checks, metrics, logs, backups and restore drills. | Hosting budget and domain/DNS authority. | Reboot/redeploy/restore test, webhook verification after restart, no public review UI. |
| P2 | Billing and pricing plan are constants only. | Add entitlement ledger, approved revision usage, invoices/GST handling and payment provider after pilot value is proven. | Founder decision on billing provider and tax process. | Test checkout/invoice/cancellation and enforced 30-revision quota. |
| P2 | Commercial support/admin workflow absent. | Add support console, error triage, onboarding checklist and customer data export/deletion. | Operations owner. | First firm can be supported without database edits or developer shell access. |
| P2 | No demand evidence in project materials. | Run structured pilot with dated consent, independent quote comparison, time/correction metrics and payment intent. | Real firms and consent. | At least several completed sessions and documented feedback, with no fabricated testimonials. |

## 12. Recommended development strategy

Repair the existing architecture. A rewrite is not justified. The current separation between model proposals, deterministic catalogue/pricing, approval, persistence and transport is a reasonable foundation. The problem is incomplete product scope and missing evidence, not an architecture that cannot be extended.

Recommended sequence:

1. Freeze the current prototype and establish a real Git baseline with a clean branch and reproducible environment.
2. Define the first paid-firm workflow narrowly. Prefer one or two high-frequency quote categories over a broad autonomous agent.
3. Build the evaluation harness and run it before changing prompts or models.
4. Generalize import and catalogue mapping with a human review screen.
5. Replace keyword revision extraction with a structured intent/state machine backed by model proposals and deterministic resolvers.
6. Add production authentication, tenant provisioning, retention, secrets, monitoring and backup restore.
7. Re-verify Meta with the chosen onboarding model and a documented one-firm pilot.
8. Add usage tracking and manual billing first. Automate payment only after successful pilot value is demonstrated.

Do not spend the next cycle on image generation, public marketing polish or a major rewrite. The highest-value proof is whether a real designer can import a real-shaped rate card, handle a representative revision correctly, approve it, and recover from ambiguity without developer help.

## 13. Questions requiring founder decisions

These cannot be resolved from code:

1. Which exact first paid workflow is the wedge: first quotations, revisions, or both?
2. Which quotation categories and units are supported in the first firm pilot?
3. Will QShift use a dedicated QShift WhatsApp number, or connect each firm's existing number through an approved Meta onboarding model?
4. Which data may be processed, where may it be stored, and how long should messages, PDFs and rate cards be retained?
5. Which model/speech provider is acceptable for production, including data-processing terms and cost limits?
6. What accuracy threshold and stop conditions are required before a quote can be sent to a client?
7. Who is the human approver and escalation contact for each firm?
8. Is the ₹999/month + GST plan still the hypothesis, and will billing initially be manual?
9. What hosting budget is authorized after the fictional pilot?
10. Which real firms will participate, and can they provide consented, sanitized examples and independent quote comparisons?

Technical choices Codex can make after those decisions include schema design, resolver structure, tests, deployment manifests, observability, retry policy and UI implementation.

## 14. Final scorecard

Scores use 0–5 where 0 means absent, 3 means a credible controlled prototype, and 5 means production evidence. **NOT VERIFIED** is used where the repository has no defensible test.

| Dimension | Score | Evidence-based justification |
|---|---:|---|
| Core quotation reliability | 3/5 | Deterministic pricing, verified rates and approval checks are tested for supported fixtures. General firm quotations and complex pricing are not supported. |
| AI extraction accuracy | NOT VERIFIED | Mock fixtures score 1.000, but real Qwen accuracy and customer-like accuracy are not measured. |
| Multilingual and voice capability | 1/5 | Synthetic text labels and a transcript fixture exist. Real multilingual audio and transcription are absent. |
| WhatsApp user experience | 2/5 | Provider-shaped local rehearsal and a separate Meta-shaped adapter exist. The simulator is not the live experience, and live Meta evidence is not in the repo. |
| Human approval security | 4/5 for prototype | Exact hash, role, expiry, replay, stale-version and rate checks are implemented and tested. Production identity/MFA/operations remain open. |
| Data import flexibility | 1/5 | CSV/XLSX exact-schema imports work. PDF/photo/OCR/ERP, aliases and mapping assistance do not. |
| Production reliability | NOT VERIFIED | Local SQLite tests and runbooks exist. No deployed uptime, PostgreSQL acceptance, restore drill or monitoring evidence. |
| Real-customer onboarding | 1/5 | Operator-provisioned fictional studio works. No self-service, Meta asset onboarding, privacy workflow or real-firm evidence. |
| Commercial readiness | 0/5 | Pricing constants and a display endpoint exist. Billing, quotas, invoices, support and payment collection are not implemented. |

## 15. Evidence appendix

### Commands and actual output

```text
pwd
/Users/eswarreddytadi/Documents/Codex/2026-11-09/referenced-chatgpt-conversation-this-is-an

git branch --show-current
master

git log -1 --oneline --decorate
fatal: your current branch 'master' does not have any commits yet

python3 --version
Python 3.11.15

make test
40 passed, 1 warning in 5.40s

make lint
Ruff: All checks passed
mypy qshift/engine qshift/approval: Success: no issues found in 4 source files

.venv/bin/python -m mypy qshift
Found 82 errors in 13 files

make eval
Offline MockLLM synthetic fixture evaluation: 180 cases
All printed fixture-label operation/line/clarification scores: 1.000

make eval-live
No live LLM adapter is configured in this offline scope.
```

### Key paths

- Authentication and modes: `qshift/api/main.py:55-104`
- Imports and rate verification: `qshift/services.py:333-553`
- Revision extraction and catalogue resolution: `qshift/services.py:556-740`
- Approval and immutable versions: `qshift/services.py:793-948`
- Project memory and PDF: `qshift/services.py:985-1114`
- Deterministic money rules: `qshift/engine/pricing.py:9-63`
- Local Qwen adapter: `qshift/agent/local_model.py:67-166`
- Deterministic revision adapter: `qshift/agent/extraction.py:45-137`
- First-quote intake: `qshift/intake.py:182-476`
- Meta webhook validation: `qshift/whatsapp_webhook.py:69-147`
- Meta text/PDF sender: `qshift/whatsapp_delivery.py:48-246`
- Pilot consent/state: `qshift/whatsapp_pilot.py:74-277`
- Pilot tests: `tests/test_whatsapp_pilot.py`
- Risk disclosures: `docs/RISKS.md`, `docs/META_FEASIBILITY.md`, `docs/PILOT_TEST.md`

### Official Meta sources checked

- [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/), last updated September 23, 2026. It covers opt-in, opt-out, templates, the 24-hour service window, automation escalation, privacy and customer-data handling.
- [WhatsApp Business Platform overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview/), current developer entry point for Cloud API, templates, media, audio, onboarding, permissions and webhooks.
- [Meta Webhooks getting started](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/), which documents HTTPS verification, SHA-256 signatures, 200 responses, retries and deduplication expectations.

### Final audit conclusion

The honest product label is: **QShift is a well-guarded, fictional-data prototype and controlled-pilot codebase for one narrow quotation workflow. It is not yet a production SaaS, a general interior-design AI agent, or a commercially validated startup.**

