# Qshift V6 implementation plan

## Completed in this local milestone

- Added a provider-independent revision extraction contract with Pydantic validation.
- Added an Ollama adapter configurable through environment variables; the adapter returns scope proposals only.
- Added deterministic grounding against tenant-scoped quotation lines and verified catalogue entries.
- Added firm-scoped catalogue aliases and migration `0010_rate_entry_aliases`.
- Added candidate lists and clarification states for ambiguous target lines or catalogue choices.
- Added quantity/dimension modification handling through the existing Decimal/paise pricing engine.
- Added safe open-draft amendment handling for model-proposed corrections; approved versions remain append-only.
- Added a versioned 55-case live evaluation set and `make eval-live` runner with raw-response capture, latency, operation metrics and held-out slices.
- Activated and measured Ollama `qwen3:1.7b`; the resulting low operation F1 is recorded in `docs/REVISION_AI_EVALUATION.md` and blocks real-firm use.
- Added regression tests for provider selection, schema validation, aliases, quantity changes and corrections.
- Added Studio UI mapping previews for rate cards and quotations, with explicit column confirmation before database writes.
- Added deterministic unmatched-item review records and Studio display after quotation import.

## Immediate next work

1. Improve multilingual extraction and source grounding, then re-run the full and held-out evaluations; do not use qwen3:1.7b for a real-firm pilot.
2. Turn unmatched-item review into a persisted correction queue with explicit authorization.
3. Expand multilingual holdout coverage with founder-reviewed fictional examples.
4. Add production identity, retention, monitoring, restore and document-access gates before any real-firm data.

## Explicitly out of scope without separate authorization

Public deployment, DNS edits, live WhatsApp messages, billing activation, paid model APIs and confidential customer data.
