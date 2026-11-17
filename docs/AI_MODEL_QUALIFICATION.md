# AI model qualification

The model proposes structured scope operations only. It cannot select authoritative prices,
approve, calculate totals or issue PDFs. Deterministic catalogue and pricing services validate
every proposal.

The locked V6.4 Qwen3 1.7B evidence is insufficient for live customer intelligence: strict F1
0.037; operation type F1 0.593; target F1 0.481; room F1 0.093; fully-correct 0.109. These are
not customer-success metrics, but they do require human correction and review.

`QSHIFT_CHANGE_MODEL_PROVIDER=mock` is the offline default. `ollama` is development-only.
`bedrock` exists as an opt-in fail-closed adapter and has not been invoked or qualified. A new
provider must run the versioned development/validation/holdout benchmark and report latency,
structured validity, wrong-target denominator, clarification quality and per-language errors.

When the model is unavailable or uncertain, keep the draft pending and ask a specific question.
