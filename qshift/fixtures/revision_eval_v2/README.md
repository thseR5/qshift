# Revision evaluation v2

This benchmark is separate from the historical 55-case `revision_eval_v1.json` run.

- `development.json` is for prompt and adapter iteration.
- `validation.json` is for bounded configuration comparisons.
- `holdout.json` is locked fictional evaluation data and must not be used to tune prompts,
  aliases or thresholds after a result is observed.

Every case has an explicit intent family, operation fields, clarification expectation,
language and difficulty. `replacement_text`, dimensions and quantities are included only
where the fictional request makes them observable. A missing gold field is not scored as a
model failure; it is reported as unmeasurable.

The benchmark uses no customer data, credentials, live WhatsApp identifiers or commercial
rate cards.
