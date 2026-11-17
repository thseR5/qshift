# Decisions

| Decision | Alternatives | Reason |
|---|---|---|
| SQLite is the default and PostgreSQL is selected through `DATABASE_URL`. | Require local PostgreSQL or add a Docker-only path. | Keep the demo portable while using SQLAlchemy types shared with PostgreSQL. PostgreSQL integration remains unverified. |
| The simulator authenticates using seeded fictional bearer tokens. | Add a production identity system. | No real identity provider or credentials are available; tokens are demo-only and must be replaced before any pilot. |
| MockLLM handles only a small deterministic set of patterns. | Allow free-form generated responses. | Keep the prototype offline, bounded to its intent allow-list and auditable. |
| Imported rate entries remain unverified until OWNER/APPROVER explicitly verifies them. | Auto-verify imported values. | Prevent untrusted spreadsheet content from becoming an approved price. |
| The quote fixture contains illustrative rates and GST is 0 for the sample. | Invent tax assumptions or claim market rates. | Every sample is fictional and is not a tax invoice or market benchmark. |
| Bundle Noto Sans (SIL Open Font License) for PDF output. | Download at runtime or rely on a host font. | Keep ₹ rendering independent of runtime network access. |

## V6 execution decisions

| Decision | Reason |
|---|---|
| Repair the current modular architecture instead of rewriting it. | The existing separation of proposal, resolver, pricing, approval and transport can support a first-customer slice. The immediate problems are coverage, onboarding and evidence. |
| Keep all live external actions gated. | Founder authorization covers local engineering only. DNS, purchases, public deployment, live WhatsApp, payment and real data require separate approval. |
| Treat `MockLLM` metrics as fixture regressions, never model accuracy. | The evaluator executes deterministic patterns, so 1.000 scores do not measure general language understanding. |
| Build onboarding around preview and explicit human verification. | Untrusted spreadsheets cannot be allowed to create authoritative rates or silently alter system rules. |

