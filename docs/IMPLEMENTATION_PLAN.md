# Qshift V6 implementation plan

## Completed in this local milestone

- Added a provider-independent revision extraction contract with Pydantic validation.
- Added an Ollama adapter configurable through environment variables; the adapter returns scope proposals only.
- Added deterministic grounding against tenant-scoped quotation lines and verified catalogue entries.
- Added firm-scoped catalogue aliases and migration `0010_rate_entry_aliases`.
- Added candidate lists and clarification states for ambiguous target lines or catalogue choices.
- Added quantity/dimension modification handling through the existing Decimal/paise pricing engine.
- Added safe open-draft amendment handling for model-proposed corrections; approved versions remain append-only.
- Added a versioned 12-case live evaluation set and `make eval-live` runner with precise offline blocker reporting.
- Added regression tests for provider selection, schema validation, aliases, quantity changes and corrections.

## Immediate next work

1. Run `make eval-live` on a local Ollama installation with `qwen3:1.7b`; review ten concrete examples and measure latency, matching and clarification metrics.
2. Add richer import mapping UI for aliases and candidate review.
3. Expand multilingual holdout coverage with founder-reviewed fictional examples.
4. Add production identity, retention, monitoring, restore and document-access gates before any real-firm data.

## Explicitly out of scope without separate authorization

Public deployment, DNS edits, live WhatsApp messages, billing activation, paid model APIs and confidential customer data.
