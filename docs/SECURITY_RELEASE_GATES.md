# Security release gates

## Required before Level 1

- Real enrolled identity resolves account + phone + sender + tenant; unknown senders are ignored.
- Invalid signatures, unsupported event types and stale timestamps cannot mutate business state.
- Duplicate inbound events and outbound idempotency keys are safe.
- All project, quote, catalogue, document and approval reads include `firm_id`.
- Approval is role-bound, content-hash-bound, expiring, single-use and stale-version safe.
- PDFs are rendered from immutable approved versions only.
- Opt-out and 24-hour/template rules are enforced by the delivery worker.

## Required before Level 2

Private PostgreSQL/S3, secret management, HTTPS, migrations, backups, restore evidence,
CloudWatch alarms, rate limits, bounded model budget, and a staging teardown are verified.

## Required before Level 3

Firm authorization, permitted data processing, Meta eligibility, qualified inference, real staff
enrollment, support escalation, incident response and a successful fictional-plus-authorized
test-number evidence pack are complete.
