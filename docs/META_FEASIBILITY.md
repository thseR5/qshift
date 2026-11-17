# Meta feasibility gate (checked 2026-11-09)

This assessment covers the published requirements for production use. The separate staff test below has a narrower scope. QShift's narrow quotation workflow may qualify as ancillary business software. Meta's terms reserve discretion over whether AI is the primary functionality.

| Question | Verdict | Notes |
|---|---|---|
| Cloud API is the supported automated messaging interface | Allowed with conditions | Use Meta's official Cloud API and current onboarding, business verification, app review and permission requirements. No unofficial clients or scraping. |
| AI-provider clause | Unknown (H1) | Terms restrict AI Providers when AI is the primary functionality, subject to Meta's determination. The current terms text surfaced during review names regional exceptions for EEA or Brazil users; neither exception covers an India-number launch. Task-specific scope is a product argument, not a guarantee. |
| Business verification and number/display-name review | Allowed with conditions | Exact eligibility and steps depend on current account/onboarding flow; verify in the live developer documentation before setup. |
| Templates and service windows | Allowed with conditions | The simulator does not send. Confirm current template categories, approval and customer-service window before implementation. |
| India price schedule | Unknown (H1) | Pricing changes and depends on category/market. Obtain current India rate card and model per-message cost before a pilot; this report does not quote stale prices. |
| User consent and opt-out | Allowed with conditions | Product needs clear opt-in, expected message types and easy opt-out. Confirm exact policy text and onboarding UX. |
| Interactive buttons, lists, Flows | Allowed with conditions | Use only supported Cloud API features and current payload/limit documentation; not validated against live endpoints. |
| Voice/media | Allowed with conditions | Official media endpoints only, promptly download ephemeral media, restrict access and retention, and apply applicable privacy/security obligations. |
| Coexistence with Business App | Unknown (H1) | Eligibility, regions, number/account prerequisites and message synchronization are not assumed; request current confirmation from Meta/official partner. |
| Groups and personal-account access | Blocked for this product design | No unsupported group automation, personal account access, or scraped messages will be built. |
| Use of business data for model training | Blocked | Do not use Business Solution Data to train general models. Provider processing must be contractually limited to the authorized service and instructions. |

## Official sources reviewed

- [WhatsApp Business Solution Terms](https://www.whatsapp.com/legal/business-solution-terms) — accessed 2026-11-09. The AI Providers clause explicitly reserves Meta's discretion over whether AI is primary and restricts use of Business Solution Data for training other models.
- [WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy) — accessed 2026-11-09. Applies to the Business Platform and API and sets messaging requirements.
- [WhatsApp Cloud API documentation](https://developers.facebook.com/docs/whatsapp/cloud-api/) — official developer entry point; current operational onboarding details must be rechecked when a live account is authorized.
- [WhatsApp pricing documentation](https://developers.facebook.com/docs/whatsapp/pricing/) — official source for current rate cards; no India values copied because the environment did not expose the live price table during this review.
- [Digital Personal Data Protection Act, 2023](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf), [DPDP Rules 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025%3B), and [commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf) — accessed 2026-11-09. The Rules have phased commencement; map obligations and dates with counsel before a pilot.

### H1 before production messaging

1. Obtain a written policy assessment for this exact task-specific product under the current AI Providers clause.
2. Verify account, number, display-name, business verification, app review, embedded signup and any coexistence requirements with official current docs or Meta.
3. Confirm current India message prices, categories, templates, user opt-in, opt-out and customer-service-window rules.
4. Approve a data processing/retention design and legal review for DPDP commencement dates and any cross-border processors.

## First WhatsApp pilot

The first pilot is a one-to-one chat for a designer or staff member using Meta's test number and fictional quotation data. The webhook passes the enrolled designer, selected project and current draft to the same conversation flow as the simulator. The agent replies with project choices, catalogue clarifications, draft totals or revision history. An authorized user signs off on the exact draft in QShift's local review screen.

The app owner reports that Meta Support confirmed the one-person fictional-data pilot for this QShift app in India. Meta also provisioned a test number and its sample message reached the owner's phone. Keep the support reply with the pilot record. Production use still requires the separate checks above. [Meta Developer Hub](https://whatsappbusiness.com/developers/developer-hub/)

The operator must authorize activation, record the one participant's opt-in, and give them a direct way to contact a human. Explain that Meta and the temporary HTTPS provider relay the staff number and fictional messages, that QShift keeps local draft changes and reply receipts for the pilot, and that `STOP` ends participation. Use participant-initiated messages. [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/)

### Receive path rehearsal

Run `make webhook-demo` to exercise the callback challenge and a signed series of incoming text events in-process. The rehearsal uses synthetic account, number and staff IDs with an isolated in-memory SQLite database. It captures QShift replies locally and skips duplicate message IDs within the run. The demo has no public URL or delivery client. [WhatsApp webhook setup](https://whatsappbusiness.com/blog/how-to-use-webhooks-from-whatsapp-business-api/) · [Official webhook signature reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/)

### Receive pilot service

The separate `qshift.whatsapp_pilot:create_app` service is disabled by default. It accepts signed text events for one configured account, test number and enrolled staff sender. It maps that sender to the seeded fictional designer. It stores project and draft context and a reply receipt with the draft update in the same database transaction. The service acknowledges the webhook without returning quote data. An operator can read captured replies from the private database. Delivery runs in a separate worker with its own switch.

To prepare a local instance, use Python 3.11 and run `make setup`. In a private shell session, set `DATABASE_URL` to a new pilot database, such as `sqlite:///./whatsapp-pilot.db`, then run:

```sh
make migrate
.venv/bin/python -m qshift.whatsapp_pilot seed
```

Set the following in the pilot process environment. Use synthetic values for local exercises. For the authorized pilot, enter the real secrets privately in your shell or a hosting secret store. Keep them out of chat, files tracked by Git and shell history.

| Setting | Value |
|---|---|
| `QSHIFT_WHATSAPP_ACCOUNT_ID` | The test messaging account ID that Meta delivers in the webhook entry |
| `QSHIFT_WHATSAPP_PHONE_NUMBER_ID` | The Phone Number ID for the Meta test number |
| `QSHIFT_WHATSAPP_STAFF_SENDER_ID` | The enrolled staff sender ID, digits only for this pilot |
| `QSHIFT_WHATSAPP_APP_SECRET` | The app secret used to validate Meta's POST signature |
| `QSHIFT_WHATSAPP_VERIFY_TOKEN` | A distinct random value of at least 24 characters used for callback verification |
| `QSHIFT_WHATSAPP_RECEIVE_ENABLED` | Set to `true` when explicitly starting the receive service |

Once the participant opts in, keep their consent record privately and give it an opaque reference such as `CONSENT-001`. Record that reference immediately before starting the pilot:

```sh
.venv/bin/python -m qshift.whatsapp_pilot consent --reference CONSENT-001
make run-whatsapp-pilot
```

The consent record is bound to this account, test number and staff sender. It expires 24 hours after recording. The webhook processes only messages from the matching staff sender during that period. QShift stores a hash of the message ID, the captured reply and the resulting draft state. The seeded rate audit records the fictional source and verification time for each verified rate. Use a fresh pilot database for each authorized session.

### Temporary HTTPS from the Mac

1. In the Meta dashboard, confirm the opted-in phone is on the WhatsApp test number's recipient list. Keep the dedicated pilot service running on `127.0.0.1:8765`.
2. For an authorized short test, install `cloudflared` if needed (`brew install cloudflared` on this Mac). In a separate terminal run `cloudflared tunnel --url http://127.0.0.1:8765`. Point it only at the pilot service. Keep the QShift review screen on the Mac.
3. In WhatsApp **Configuration**, enter the resulting `https://<temporary-host>/webhooks/whatsapp` as the callback, supply the private verify token and subscribe to `messages`. Keep the tunnel and Mac running during the test. If the tunnel restarts, enter its new address in Meta. [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) · [Meta's webhook configuration guide](https://whatsappbusiness.com/blog/how-to-use-webhooks-from-whatsapp-business-api/)
4. Ask the staff participant to send `projects` from the enrolled phone. Use `.venv/bin/python -m qshift.whatsapp_pilot replies` in a private shell with the same pilot settings to check whether QShift captured the message before enabling replies.

The tunnel creates a public endpoint for callback verification and signed messages. Use default tunnel logging and leave Uvicorn access logging off so the local server avoids recording the verification query string. Cloudflare relays the HTTPS requests. The temporary URL has no uptime guarantee. See [stable AWS hosting](HOSTING.md) for the containerized PostgreSQL setup.

### Staff replies

With the same pilot settings, preview replies without contacting Meta:

```sh
.venv/bin/python -m qshift.whatsapp_delivery preview
```

Run both processes against the same private pilot database. Run one delivery worker for the initial pilot.

When the live pilot is authorized, supply these additional values through the worker's private environment:

| Setting | Value |
|---|---|
| `QSHIFT_WHATSAPP_SEND_ENABLED` | `true` when explicitly activating replies |
| `QSHIFT_WHATSAPP_ACCESS_TOKEN` | The private test-app token with WhatsApp messaging permission |
| `QSHIFT_WHATSAPP_GRAPH_VERSION` | The Graph API version supported by the Meta app |

Have the enrolled staff member start the conversation on their phone. To check one eligible reply, run `.venv/bin/python -m qshift.whatsapp_delivery run --once`. After confirming receipt on the phone, the continuous worker is `.venv/bin/python -m qshift.whatsapp_delivery run`.

For the first conversation, send `use project-sharma`, then “Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.” Reply `choose COUNTER-QUARTZ-CALACATTA` when asked. The fictional draft should total ₹2,43,200.

For human review, start the normal QShift app in a private terminal using the same pilot `DATABASE_URL` and keep it bound to `127.0.0.1`:

```sh
.venv/bin/uvicorn qshift.api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, select Sharma Residence and type `status` to load the WhatsApp draft into the review panel. Switch to the Approver role to inspect and approve the exact fictional revision. The approval and PDF stay in QShift.

The worker sends text to the enrolled recipient within 24 hours of the specific incoming message. It skips missing and expired timestamps and suppresses queued replies after `STOP`, `unsubscribe` or `opt out`. It records an attempt before calling Meta and leaves failures and uncertain outcomes for manual review. The `accepted` state means Meta accepted the API request. Check the phone for delivery. The first pilot needs a live test of the actual Meta API and account. [Meta's text message request](https://www.postman.com/meta/whatsapp-business-platform/request/8gvd47s/send-text-message) · [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/)

At the end, stop the reply worker, tunnel and webhook, and remove the temporary callback from Meta. Review the local draft and delivery audit, then clear the dedicated pilot database as agreed with the participant.

