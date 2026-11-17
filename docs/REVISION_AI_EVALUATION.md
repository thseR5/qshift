# Revision AI evaluation — v1

Evaluation set: `qshift/fixtures/revision_eval_v1.json` (12 fictional requests).

## Run status

`make eval-live` was run on 2026-11-17. It did not execute a model case because Ollama was unavailable at `http://127.0.0.1:11434/api/chat`. No model was downloaded and no paid provider was contacted.

Therefore the live operation precision, recall, F1, matching accuracy, wrong-item rate, clarification metrics and latency are **not available**. The table below is a transparent list of planned cases, not fabricated model output.

| Case | Language | Expected behavior | Actual live result |
|---|---|---|---|
| en-01 | English | MODIFY guest-bedroom wardrobe dimensions | Not executed — Ollama unavailable |
| en-02 | English | REPLACE kitchen granite; REMOVE guest-bedroom ceiling; clarify catalogue | Not executed — Ollama unavailable |
| en-03 | English | ADD living-room skirting; require verified rate/quantity | Not executed — Ollama unavailable |
| hi-01 | Hindi | REPLACE kitchen granite; REMOVE guest-bedroom ceiling | Not executed — Ollama unavailable |
| hinglish-01 | Hinglish | MODIFY guest-bedroom wardrobe width | Not executed — Ollama unavailable |
| telugu-01 | Telugu | REPLACE kitchen granite; REMOVE guest-bedroom ceiling | Not executed — Ollama unavailable |
| roman-telugu-01 | Romanized Telugu | MODIFY guest-bedroom wardrobe dimensions | Not executed — Ollama unavailable |
| correction-01 | English | CORRECT_PREVIOUS_CHANGE to living-room ceiling | Not executed — Ollama unavailable |
| ambiguous-01 | English | REPLACE countertop but require target clarification | Not executed — Ollama unavailable |
| injection-01 | English | Ignore injection; process only the explicit ceiling removal | Not executed — Ollama unavailable |

The offline `make eval` result remains MockLLM fixture evidence only: 180 curated cases, not a claim about real language understanding.

## Safe execution once Ollama is available

1. Start Ollama and make the approved local model available.
2. Set `QSHIFT_CHANGE_MODEL_PROVIDER=ollama` and optionally `QSHIFT_CHANGE_MODEL=qwen3:1.7b`.
3. Run `make eval-live`.
4. Review failures and ten concrete expected-versus-actual examples before any real-firm pilot.
