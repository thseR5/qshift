# Qshift demo (3 minutes)

Everything in this run is marked SIMULATED and uses fictional records.

| Time | Action | What to point out |
|---|---|---|
| 0:00 | Start `make clean-demo && make demo` or open the browser simulator. | SIMULATED banner; fictional Sharma Residence; no external send. |
| 0:20 | Pin Sharma Residence. | Project context comes from an explicit pin, not a guess from forwarded text. |
| 0:40 | Play the Telugu-English transcript fixture and confirm it. | The transcript is echoed before consequential changes are drafted. |
| 1:00 | Inspect the extracted ceiling removal and countertop replacement. | Structured operations only; unresolved catalogue choice blocks approval. |
| 1:20 | Choose a verified Calacatta quartz option. | The backend recalculates from the verified rate in integer paise. |
| 1:40 | Switch to an APPROVER and approve. | Exact draft hash, role, expiry, current base version and replay are checked server-side. |
| 2:05 | Open the generated PDF and version history. | Approved version is appended; the previous version remains. |
| 2:35 | Ask for project changes. | Response is assembled from stored operations and reports its synthetic-record scope. |

## Expected output

The initial illustrative quote is ₹2,28,200. The Calacatta quartz selection plus ceiling removal produces a ₹15,000 net increase and a ₹2,43,200 revised quote. These are fictional demonstration numbers only.

## Fallback

The local demo uses MockLLM and MockTranscriber and makes no provider calls. If the web interface is unavailable, `make demo` runs the same service workflow and prints the PDF path, history and project-memory result. `make clean-demo` safely resets only `qshift.db` and `demo-output/` in the current directory.

