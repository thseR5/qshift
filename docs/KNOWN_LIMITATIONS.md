# Qshift known limitations

This file is intentionally explicit. A limitation is not a hidden roadmap commitment.

- The default offline revision provider remains deterministic `MockLLM`; the production-oriented Ollama adapter is available only when explicitly configured.
- Real-model accuracy is currently unmeasured because Ollama is not running in this environment. `make eval-live` reports the precise blocker without downloading a model.
- Local Ollama `qwen3:1.7b` supports only the narrow wardrobe and two-item intake prompts.
- The versioned live revision set contains 55 fictional English, Hindi, Hinglish, Telugu and Romanized Telugu cases, but it has not produced metrics without a running local model.
- Voice is a transcript fixture. Real audio download, decoding and speech transcription are not implemented.
- Rate-card and quotation imports support simple CSV/XLSX schemas. PDF, scan, image and ERP ingestion are not implemented.
- Import matching supports exact SKU, firm-scoped aliases and deterministic candidate lists; ambiguous matches still require a designer selection. Semantic/fuzzy ranking and PDF/photo extraction are not implemented.
- Discounts, package pricing, labor dependencies, minimum charges and historical effective rates are not implemented.
- Project memory is a seven-day deterministic operation summary, not semantic memory.
- Simulated WhatsApp is not proof of live Meta behavior. The repository does not contain independently reproducible live Meta evidence.
- Production authentication, MFA, recovery, secret management, retention enforcement, deletion, monitoring, backups and restore drills are incomplete.
- Billing and usage enforcement are not implemented. The displayed ₹999 plan is a hypothesis.
- PostgreSQL compatibility is a target, not a production scalability or restore claim.
- The repository has a committed local baseline and subsequent implementation commits; uncommitted `.DS_Store`/`tmp/` files are intentionally excluded.
