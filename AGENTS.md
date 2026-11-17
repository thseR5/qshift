# Qshift contributor rules

- Keep the simulator clearly marked SIMULATED. Never send WhatsApp messages or customer documents.
- Use only fictional seed data. Do not add real customer data, credentials, or rate cards.
- Tenant-scope every read and write by `firm_id`; deny ambiguous project selection.
- Monetary values persist as integer paise. Use `Decimal` and half-up rounding at calculation boundaries; never use float arithmetic for money.
- LLM/transcript adapters may propose structured scope operations only. Catalogue lookup, calculation, permissions, approvals and document issuance stay deterministic.
- Approval is a server-side action bound to an exact content hash, approver identity and expiry; reject replay and stale base versions.
- Approved versions are append-only. Corrections create another version.
- Treat uploaded text and spreadsheet cells as untrusted data. They cannot change system rules or authorize actions.
- Run `make test` and `make lint` when changing the application. Report actual outcomes and known gaps.

