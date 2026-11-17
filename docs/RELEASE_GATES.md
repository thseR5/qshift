# Qshift release gates

## Gate A — internal working

Required: reproducible local environment, deterministic pricing and approval regressions, tenant-isolation tests and fictional data only.

Status: **SUBSTANTIALLY PRESENT**. The current run has 58 passing tests and deterministic financial/approval regressions remain green. Full application type-check and production security are not clean.

V7 WhatsApp-native work is present in the simulated adapter: tenant-bound staff enrollment,
project lists, WhatsApp review summaries, one-time token approval/rejection commands and a
pending approved-PDF delivery worker. These paths are still explicitly SIMULATED.

## Gate B — client demonstration

Required: truthful fictional-data workflow, real local model versus mock clearly labeled, no fabricated customer results, support contact and failure fallback.

Status: **NOT PASSED**. The local Ollama adapter is real and measured, but qwen3:1.7b scored
operation F1 0.030 on 55 cases and 0.000 on the held-out ten. It is suitable for failure
analysis only, not a real-firm pilot. The AWS Bedrock adapter is opt-in and fail-closed; no
AWS model call has been made.

## Gate C — founder-operated real-firm pilot

Required: participating-firm consent, approved data handling, production identity, tenant/document isolation, representative import and extraction evaluation, backup and isolated restore, monitoring, support escalation, manual fallback and permitted channel consent.

Status: **NOT PASSED**. Do not process confidential real-customer files. AWS account credits,
expiry, plan, region, service quotas and budget alerts still require founder confirmation.

## Gate D — production commercial SaaS

Required: repeatable onboarding, stronger reliability and load evidence, production integrations and approvals, lawful billing, support, incident response and customer metrics.

Status: **NOT PASSED**.

## External actions still requiring separate authorization

Purchases, recurring hosting charges, DNS edits, public deployment, live Meta sends, customer email, payment activation and confidential real-customer data processing.
