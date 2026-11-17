# Qshift — offline-first WhatsApp quotation agent

Qshift turns fictional client messages into a draft first quote for the designer to review. The **SIMULATED** first-quote workflow runs entirely locally alongside the existing scope-change simulator. A separate, disabled-by-default adapter supports a staff pilot on Meta's test number.

All built-in company, project, quotation, and rate data is explicitly fictional and illustrative, not market pricing.

## Quick start

Python 3.11 is required.

```sh
make setup
make migrate
make run
```

Open `http://127.0.0.1:8000`. The app seeds a fictional demo tenant on first use.

In the simulator chat, type `projects`, then `use project-sharma`. Describe a change such as “Replace the kitchen granite with quartz”, then reply with `choose` and one of the SKUs offered. Use `status` to reopen an active draft, `history` for approved revisions, or `changes` for recent requests. An authorized user approves the exact revision in the review panel.

Demo roles use fictional local bearer tokens: Designer `demo-designer-token`, Approver `demo-approver-token`, Owner `demo-owner-token`. The UI lets you switch roles to demonstrate that drafting and approval permissions differ. These are not suitable for a shared or production deployment. The demo seed endpoint exposes the preset fictional accounts by design; do not expose this app to the public internet.

## First quote from a simulated client chat

1. Open `http://127.0.0.1:8000/intake` and choose **Start new sample**.
2. Use **Fill example message** and **Send in simulator** for each message. The client asks for a wardrobe in the second bedroom, specifies white laminate and an 8-foot width, then answers Qshift's height question with 7 feet.
3. The initial draft is 56 sq ft at a fictional ₹1,250 per sq ft, for ₹70,000. Follow the source links in the brief to check which message supplied each detail.
4. Optionally change the billable area and recalculate. Switch to **Dev · Approver** and approve the reviewed quote.
5. Download the approved v1 PDF from its delivery bubble in the simulated chat. Refreshing restores that conversation in the current browser tab.
6. Open **View AI concept preview** to see a bundled AI-generated wardrobe illustration. After approval, **Dev · Approver** can attach the preview in the simulated client chat. It is a separate illustration, and the quote and PDF keep their approved contents.

The demo supports one white-laminate wardrobe and explicitly stated dimensions in feet, using a deterministic offline extractor. It uses the real catalogue, calculation, approval, version and PDF services, with no external delivery. The bundled concept is a pre-generated sample, so opening a preview does not call an image API or use the client conversation as a prompt. The existing revision simulator is still available at `/`.

For local AI intake, run Ollama on `127.0.0.1:11434`, pull `qwen3:1.7b`, and start QShift with `QSHIFT_INTAKE_MODEL=ollama make run`. Start a new fictional sample. The local model reads the conversation and proposes source-linked scope fields. QShift validates those fields, looks up the verified catalogue rate, calculates the quote, and requires human approval. If the model fails, this mode returns an error and lets you retry the message.

### Natural-language revision extraction

Revision extraction is provider-configurable. The safe default is the deterministic `mock` provider used by offline tests. To use a locally running Ollama model for revision proposals, set `QSHIFT_CHANGE_MODEL_PROVIDER=ollama` (and optionally `QSHIFT_CHANGE_MODEL`, `QSHIFT_OLLAMA_URL`, and `QSHIFT_CHANGE_TIMEOUT_SECONDS`). Ollama output is validated against a Pydantic schema and treated as an untrusted scope proposal. It cannot choose a rate, approve a draft, or issue a PDF. If the model is unavailable, Qshift creates a manual-review draft rather than mutating the quotation.

Use `make eval-live` to run the versioned fictional revision set against the configured local model. It records raw model responses, normalized proposals, validation errors and latency. It never downloads a model or contacts a paid provider automatically. The measured `qwen3:1.7b` result is documented in `docs/REVISION_AI_EVALUATION.md` and is not a release-quality accuracy claim.

With local AI enabled, choose **Start two-item AI sample**. The example quotes a second-bedroom wardrobe and a living-room gypsum ceiling. Answer the ceiling-area follow-up with **100 sq ft**. The initial quote is ₹78,500. Use the ceiling line’s **Recalculate** button to change its billable area to 90 sq ft, which brings the quote to ₹77,650. Switch to **Dev · Approver**, approve, and download the approved PDF from the simulated chat. All quantities and rates are fictional. This intake supports one of each of the two sample items.

### Simulated WhatsApp client rehearsal

With local AI running, open **Simulated WhatsApp rehearsal** on `/intake`.

1. Import the fictional rate card. Switch to **Dev · Approver** and verify both rates.
2. Start a WhatsApp rehearsal and send both example messages. They enter through the local provider-shaped webhook. The server routes the fictional sender to a single project and records each message ID to handle retries.
3. Review and approve the draft. Approval stores the exact PDF bytes for that conversation, and the simulated client chat offers a download.

For an automated run, use `make client-demo` after starting the app on port 8078, or `make client-demo PORT=8000` if you started it with `make run`. The command uses the real local model, imports and verifies the fixture card, replays an inbound event, checks the approved PDF hash, and verifies another chat cannot retrieve the PDF.

The simulator uses fake account, number and client identifiers and local demo authentication. The live WhatsApp staff adapter stays separate. A production rollout still requires secure identities, authorized WhatsApp onboarding and delivery, hosted operations, billing, and real pilot validation.

### Signed-in studio workspace

Run a separate local database for the fictional studio:

```sh
DATABASE_URL=sqlite:///./work/studio.db make migrate
DATABASE_URL=sqlite:///./work/studio.db .venv/bin/python -m qshift.studio_auth maple owner --name "Fictional Owner" --firm-name "Maple Demo Studio"
DATABASE_URL=sqlite:///./work/studio.db make studio
```

Create your local password when prompted. Open `http://127.0.0.1:8079` and sign in as studio `maple`, username `owner`. Create a project, download and import the fictional rate card, verify its entries, and use **Start simulated client chat**. You can provision a separate designer or approver into the same studio by omitting `--firm-name` and specifying `--role DESIGNER` or `--role APPROVER`. Run Ollama locally with `qwen3:1.7b` for the quote workflow.

Studio sign-in uses server-side revocable sessions with an eight-hour expiry. The studio process accepts same-origin writes and listens on loopback. It has no public registration and ignores demo bearer tokens. The owner, designer, and approver roles are assigned by the local operator. Customer-facing identity, account recovery, production authorization review, and live delivery remain launch work. Keep test databases and local passwords out of source control.

## Three-minute offline demo

```sh
make clean-demo
make demo
```

The script resets the local fictional data, pins Sharma Residence, confirms the fixture transcript of the Telugu-English request, asks for a verified quartz catalogue choice, calculates the net change, approves as an APPROVER, creates a PDF, prints version history, and queries stored project records. The generated PDF is in `demo-output/`.

For the browser version, start `make run`, pin Sharma Residence, choose **Use Telugu voice fixture**, confirm the transcript, select a quartz option, switch to an Approver, approve, then open version history and project changes.

## Developer commands

- `make setup` — install the package and development tools.
- `make migrate` — apply the Alembic migrations.
- `make test` — run unit, workflow, API, and property tests with coverage output.
- `make lint` — run Ruff and strict mypy on the engine/approval packages.
- `make eval` — report offline synthetic fixture scores by language.
- `make eval-live` — run the 55-case real-model evaluation when Ollama is configured; use `QSHIFT_EVAL_START`/`QSHIFT_EVAL_LIMIT` for a slice.
- `make eval-forensics` — decompose a completed live JSONL run into intent, operation, target, room and clarification metrics.
- `make diagnose-generation` — run a small controlled comparison of context and output-token settings; it does not tune or download a model.
- `make demo` — run the repeatable offline scenario.
- `make clean-demo` — delete only local demo database and generated demo PDFs.

The synthetic set contains 180 labeled messages across English, Hindi, Telugu and noisy transcript fixtures, plus 20 prompt-injection examples. The reported 1.00 fixture scores are deterministic pattern matches and do not predict real-world model performance.

## Imports

Rate-card CSV/XLSX imports accept the canonical columns `sku,name,category,unit,rate_paise,gst_bps,aliases` plus safe aliases such as `Item Code`, `Description`, `UOM`, `Unit Price`, `GST %` and `Synonyms`. Use `POST /api/imports/rate-card/preview` to inspect the detected mapping without writing the database. Imported rows start unverified. An OWNER or APPROVER must verify rates before the catalogue can use them. Aliases are inert firm-scoped metadata used only for candidate matching.

Quotation CSV/XLSX imports accept `room,sku,quantity` plus safe aliases such as `Room Name`, `Item Code`, `Qty` and `Space`. Use `POST /api/imports/quotation/preview` for a read-only mapping preview. Only SKUs already verified for the firm are accepted. The import response includes `unmatched_items` with deterministic verified-SKU suggestions for review; it does not silently accept or verify them. PDF and photo extraction is intentionally unsupported.

Blank CSV and XLSX templates are in `qshift/fixtures/templates/`.

Money is stored as integer paise. Quantity is parsed as `Decimal`; line totals round half up to the nearest paise. GST is grouped by basis-point slab and rounded half up per slab subtotal. Indian digit grouping is used for display. Seed GST is 0 bps and is illustrative, not tax guidance.

## Configuration

Copy `.env.example` to `.env` if you want to change the settings. Set `DATABASE_URL` to a SQLAlchemy URL for PostgreSQL 16 when one is available. SQLite is the tested offline default. `QSHIFT_LLM_PROVIDER=mock` and `QSHIFT_TRANSCRIBER=mock` keep intake processing offline. Revision extraction uses `QSHIFT_CHANGE_MODEL_PROVIDER=mock` unless explicitly set to `ollama`. `QSHIFT_APPROVAL_SECRET` is for local demonstration only and must be a unique, managed secret before any real environment.

## India founding plan

The first 10 firms get ₹999 per month or ₹9,990 prepaid per year, with a 12-month price lock. Both payment schedules include one firm, three users and 30 revisions per month. Count one revision per newly approved quote version. Overage is ₹25 per extra approved revision with opt-in. Founding onboarding and rate-card cleanup are included. GST is extra where applicable. The planned list price is ₹2,499 per month after the founding cohort and a usage review.

The app displays the offer from `/api/pricing`. Billing and quota enforcement are pending for customer launch.

## Architecture and documents

- [Architecture and data flow](docs/ARCHITECTURE.md)
- [Product requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Mode comparison](docs/MODES.md)
- [Tool permissions](docs/TOOL_PERMISSIONS.md)
- [Database and project memory](docs/DATA_MODEL.md)
- [Meta feasibility gate](docs/META_FEASIBILITY.md)
- [Stable AWS Lightsail hosting for the staff pilot](docs/HOSTING.md)
- [Risks and limitations](docs/RISKS.md)
- [3-minute demo script](DEMO_SCRIPT.md)
- [Roadmap](docs/roadmap/README.md)
- [Pilot test methodology](docs/PILOT_TEST.md)

For the staff-only WhatsApp pilot and reply preview, see the local setup in the [Meta feasibility notes](docs/META_FEASIBILITY.md#receive-pilot-service). Run `make webhook-demo` to rehearse the same webhook protocol with fictional data.

To run an authorized, one-tester first-quotation pilot with a Meta test number,
follow [the ₹0 WhatsApp setup](docs/WHATSAPP_TEST.md).

## Security and limitations

The service layer scopes lookups by `firm_id`; approval requires a server-issued token tied to the exact draft content, approver, expiry and base version. Replay, cross-approver use and stale revisions are rejected. This is not production authentication: it has seeded demo bearer tokens, no MFA, no session lifecycle, no encrypted storage, and no production deployment hardening. Run locally with fictional content only.

An open revision can be safely cancelled with `cancel`, `discard` or `stop` after the project is selected. Cancellation marks only the draft as cancelled and leaves the last approved quote version unchanged.

The WhatsApp pilot adapter is disabled by default and has been tested locally with a simulated Meta connection. LLM and transcription run from offline fixtures. See `docs/HOSTING.md` for the containerized PostgreSQL setup and `docs/RISKS.md` for the remaining customer launch work.

