# Risks and limitations

- **Meta eligibility:** The app owner reports case-specific Meta Support confirmation for a one-person fictional-data test in India. Production eligibility still needs confirmation under the current terms.
- **Identity and onboarding:** The separate loopback studio process has operator-provisioned accounts and revocable sessions. It rejects demo bearer tokens. The legacy demo still uses fixed fictional accounts. Production identity review, MFA, recovery, and security monitoring remain open.
- **PostgreSQL:** The local PostgreSQL 16 container rehearsal exercised TLS certificate validation, migrations, concurrent duplicate webhook requests and draft recovery after a restart. Managed AWS connectivity and backup restoration still need a deployment check.
- **Import safety:** CSV/XLSX imports validate required fields and keep new rates unverified. They do not yet produce a full downloadable validation workbook, robust outlier review, virus scanning, or formula-injection quarantine/export rules.
- **Quotation import:** Only simple itemized CSV/XLSX with a verified SKU, room and quantity is accepted. PDF/photo/OCR import is out of scope.
- **Extraction:** First-quote intake can use local Qwen3 1.7B and validate scope against client message evidence. The demo catalogue supports one wardrobe and one gypsum ceiling. The separate revision adapter uses deterministic rules. Neither fixture results nor the local model smoke test measure production accuracy or multilingual reliability.
- **Voice:** A transcript fixture is used. No media upload, audio decoding, encryption or real transcription provider is implemented.
- **Approval race safety:** Version/base/hash/replay checks are implemented, but concurrency has not been stress-tested against PostgreSQL.
- **PDF font:** Noto Sans variable font is bundled under its SIL Open Font License. Visual embedding/rendering still needs review on non-macOS clients.
- **Privacy:** The staff pilot requires a documented opt-in and uses a private test database. The operator handles end-of-test deletion. Production retention, deletion requests, processor agreements and legal review remain open.
- **Commercial launch:** Confirm Meta eligibility and production account onboarding. Establish production identity, tenant provisioning, stable hosting, backup restoration and data retention. Expand verified catalogue matching and test the workflow with authorized pilot firms. Paid operation also requires billing, usage tracking and support.

