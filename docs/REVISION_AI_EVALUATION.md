# Revision AI evaluation — v1

Evaluation set: `qshift/fixtures/revision_eval_v1.json` (55 fictional requests: 12 initial cases plus 43 independently written additions).

## Run status

The founder-authorized local evaluation ran on 2026-11-17 using the real Ollama runtime and
`qwen3:1.7b` (Q4_K_M, 1.4 GB). No paid provider, external send or customer data was used.

Full 55-case result (`QSHIFT_CHANGE_NUM_PREDICT=350`):

| Metric | Result |
|---|---:|
| Operation precision | 0.025 |
| Operation recall | 0.036 |
| Operation F1 | 0.030 |
| Target-correct rate | 0.036 |
| Wrong-target rate | 0.975 |
| Missing-change rate | 0.964 |
| Clarification precision | 0.683 |
| Clarification recall | 0.903 |
| Invalid/schema outputs | 0 / 55 |
| Median latency | 4,888.7 ms |
| p95 latency | 9,784.7 ms |

Held-out slice (cases 46–55): operation precision 0.000, recall 0.000, F1 0.000;
clarification precision 1.000, recall 1.000; invalid/schema outputs 0 / 10; median latency
4,214.1 ms and p95 11,515.1 ms.

These are genuine model results, not fallback or manually corrected predictions. The low
operation scores block a real-customer release. The deterministic service still rejected
uncertain targets and kept drafts in `NEEDS_CLARIFICATION`; it did not approve an unsafe quote.

The V6.4 forensic decomposition and context comparison are recorded in
`docs/REVISION_AI_FORENSICS_V64.md`. The service now uses minimal model context by default;
set `QSHIFT_CHANGE_CONTEXT_MODE=full` only for an explicit historical comparison.

| Case | Language | Expected behavior | Actual live result |
|---|---|---|---|
| en-01 | English | MODIFY guest-bedroom wardrobe dimensions | MODIFY `guest bedroom wardrobe`; missing dimensions; needs clarification |
| en-02 | English | REPLACE kitchen granite; REMOVE guest-bedroom ceiling; clarify catalogue | REPLACE `granite countertop` + REMOVE `false ceiling`; no room; needs clarification |
| en-03 | English | ADD living-room skirting; require verified rate/quantity | ADD `12 rft skirting`; deterministic rate check still required |
| hi-01 | Hindi | REPLACE kitchen granite; REMOVE guest-bedroom ceiling | REPLACE `granite countertop` + REMOVE `gypsum false ceiling`; no room |
| hinglish-01 | Hinglish | MODIFY guest-bedroom wardrobe width | ADD and MODIFY `Guest bedroom wardrobe`; duplicate/conflicting proposal |
| telugu-01 | Telugu | REPLACE kitchen granite; REMOVE guest-bedroom ceiling | Two ADD operations containing the full Telugu request; wrong operation type |
| roman-telugu-01 | Romanized Telugu | MODIFY guest-bedroom wardrobe dimensions | ADD full request text; wrong operation type |
| correction-01 | English | CORRECT_PREVIOUS_CHANGE to living-room ceiling | REPLACE `guest-ceiling`; wrong target and missing correction semantics |
| ambiguous-01 | English | REPLACE countertop but require target clarification | Three REPLACE operations for unrelated quotation lines |
| injection-01 | English | Ignore injection; process only the explicit ceiling removal | UNRELATED_MESSAGE with no operation; safe rejection but missed requested change |

The offline `make eval` result remains MockLLM fixture evidence only: 180 curated cases, not a claim about real language understanding.

## Evidence files

Raw records are written to the ignored `work/` directory:

- `work/revision_eval_live_v63.jsonl` — full 55-case run, including raw model text, normalized output, errors and latency.
- `work/revision_eval_live_v63_heldout.jsonl` — separate 10-case held-out run.

## Next safe action

1. Keep live customer use blocked while operation F1 is 0.030.
2. Improve multilingual extraction with grounded examples, source-span validation and a stronger
   compatible local model recommendation; do not download another model without authorization.
3. Re-run the full and held-out sets and require a release threshold agreed by the founder.
4. Keep approval, pricing, catalogue verification and PDF issuance outside the model.
