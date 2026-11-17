# Roadmap (design only after Phase 2)

## Phase 3 — Live pilot readiness (design only)

**Entry criteria:** H1 Meta policy and account eligibility confirmation; H2 explicit real-pilot authorization; production identity, DPDP review, retention/deletion, incident response and PostgreSQL concurrency tests complete. **Risks:** uncertain policy, customer-data handling, price errors, account restrictions. **Test plan:** sandbox contract tests, security review, consent/opt-out checks, monitored staff-only pilot, human approval audit, rollback and data-deletion drill.

## Phase 4 — Connected Business Account (design only)

Use official Meta onboarding only after documented eligibility for the exact account. Verify coexistence, supported conversation synchronization, permissions, webhooks, message window, templates, media handling and app review from current official docs. **Risks:** unsupported account type, partial sync, duplicates/out-of-order events, pricing changes. **Test plan:** signed payload verification, idempotency and ordering, opt-in/out, retry behavior, webhook availability and human escalation. No personal accounts, unsupported groups or scraping.

## Phase 5 — Controlled client-facing requirements agent (design only)

Only after the designer workflow is trusted. Disclose automation; collect requirements and route questions to a human. Never quote, negotiate, discount, promise dates or approve. **Risks:** client confusion, unauthorized commercial commitments, privacy and language errors. **Test plan:** adversarial role boundaries, disclosure comprehension, escalation, consent withdrawal and red-team prompt injection.

## Phase 6 — Commercial SaaS (design only)

Add tenant onboarding, managed identity, billing, support, observability, data export/deletion and service operations only after pilot evidence and a security review. **Risks:** market willingness-to-pay, support burden, legal/compliance costs and message economics. **Test plan:** tenant isolation, load/concurrency, migration rollback, backup restore, billing correctness, incident drills and customer usability studies.

