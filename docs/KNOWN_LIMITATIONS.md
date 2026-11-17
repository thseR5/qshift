# Qshift known limitations

This file is intentionally explicit. A limitation is not a hidden roadmap commitment.

- The default offline revision provider remains deterministic `MockLLM`; the production-oriented Ollama adapter is available only when explicitly configured.
- Real-model accuracy is now measured, but poor: qwen3:1.7b produced operation precision 0.025, recall 0.036 and F1 0.030 on 55 cases; the held-out ten scored F1 0.000. It must not be used for a real-firm pilot.
- Local Ollama `qwen3:1.7b` emits schema-valid JSON but frequently confuses ADD/MODIFY/REPLACE, drops rooms, copies quotation context, and mishandles Telugu/Hinglish. The backend keeps uncertain outputs in manual review.
- The versioned live revision set contains 55 fictional English, Hindi, Hinglish, Telugu and Romanized Telugu cases with raw model evidence in ignored `work/` files.
- Voice is a transcript fixture. Real audio download, decoding and speech transcription are not implemented.
- Rate-card and quotation imports support simple CSV/XLSX schemas. PDF, scan, image and ERP ingestion are not implemented.
- Import matching supports exact SKU, firm-scoped aliases and deterministic candidate lists; ambiguous matches still require a designer selection. Semantic/fuzzy ranking and PDF/photo extraction are not implemented.
- Quotation imports now return unmatched-item review records and deterministic verified-SKU suggestions; the review workflow is not yet a persisted correction queue.
- Discounts, package pricing, labor dependencies, minimum charges and historical effective rates are not implemented.
- Project memory is a seven-day deterministic operation summary, not semantic memory.
- Simulated WhatsApp is not proof of live Meta behavior. The repository does not contain independently reproducible live Meta evidence.
- Production authentication, MFA, recovery, secret management, retention enforcement, deletion, monitoring, backups and restore drills are incomplete.
- Billing and usage enforcement are not implemented. The displayed ₹999 plan is a hypothesis.
- PostgreSQL compatibility is a target, not a production scalability or restore claim.
- The repository has a committed local baseline and subsequent implementation commits; uncommitted `.DS_Store`/`tmp/` files are intentionally excluded.
