# Qshift startup launch status

## A. Actual release level

**Level 0 — offline demonstration.** The verified journey uses fictional data, local SQLite,
the official-shaped simulated webhook adapter and local PDF generation. No AWS service or live
Meta message is verified.

## B. What is live

| Surface | Evidence | State |
|---|---|---|
| Local FastAPI/worker | `make demo`, `make webhook-demo` | VERIFIED locally |
| AWS services | account checklist; AWS CLI unavailable | NOT VERIFIED |
| Meta inbound | signed simulated adapter | SIMULATED |
| Meta outbound | sender code and delivery state model | NOT VERIFIED |
| AI inference | mock by default; Ollama measured; Bedrock fail-closed adapter | QUALIFICATION ONLY |
| PDF delivery | local exact-version PDF | VERIFIED fictional data |

## C. Complete fictional journey

`projects` → `use project-sharma` → forwarded change → catalogue choice → `review` →
`approve <one-time-token>` → immutable version → pending PDF worker → delivery state and history.
The direct smoke run returned `accepted` and a valid PDF header. Every step was simulated/local.

## D. Security readiness

Verified: tenant-scoped queries, signed webhook validation, duplicate receipt/event guards,
role checks, hash-bound expiring single-use approvals, immutable versions, integer-paise pricing,
redacted recipient hashes, opt-out suppression and fail-closed model/provider boundaries.

Unresolved: production identity proof, secure media download/retention, AWS secrets/IAM, backups,
external delivery-status reconciliation with a real provider, Meta eligibility and customer-data
review, and a qualified production inference model.

## E. AWS

Region, resource state, credits, expiry, plan and charges: **NOT VERIFIED**. AWS CLI is not
installed. Run `scripts/aws/account_checklist.sh`, then confirm Billing > Credits/Free Tier and
use the Pricing Calculator. No AWS resources were created.

## F. AI

Qwen3 1.7B remains unsuitable as a live default: the locked V6.4 evaluation reported strict F1
0.037, operation-type F1 0.593, target F1 0.481, room F1 0.093 and fully-correct 0.109. The
Bedrock adapter is disabled unless explicitly enabled and qualified. Human review is mandatory.

## G. Code quality

`make test`: **58 passed, 1 warning**. `make lint`: Ruff and configured mypy passed. The latest
V8 identity/delivery work is committed in the current Git history; untracked `.DS_Store` and
`tmp/` files are pre-existing and untouched.

## H. Immediate blockers

1. Founder confirms AWS account/region/credit budget and authorizes staging resources.
2. Account owner verifies Meta commercial eligibility, phone-number identity and messaging policy.
3. Implement/authorize Meta media retrieval and test it only with fictional files.
4. Qualify a multilingual inference provider on the locked holdout.
5. Complete staging backup/restore and real provider status-event tests.

## I. Demonstration procedure

```text
make test
make lint
make demo
make webhook-demo
```

For the full approval/PDF smoke path, use an enrolled fictional APPROVER and the conversation
sequence in `docs/WHATSAPP_CUSTOMER_JOURNEY.md`.

## J. Next milestone

**Level 1** is the shortest next milestone: run the same fictional workflow against an authorized
Meta test number, record provider message IDs and status events, and keep all customer data out.
