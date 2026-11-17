# Qshift release gates

## Gate A — internal working

Required: reproducible local environment, deterministic pricing and approval regressions, tenant-isolation tests and fictional data only.

Status: **SUBSTANTIALLY PRESENT**. The current run has 54 passing tests and deterministic financial/approval regressions remain green. Full application type-check and production security are not clean.

## Gate B — client demonstration

Required: truthful fictional-data workflow, real local model versus mock clearly labeled, no fabricated customer results, support contact and failure fallback.

Status: **NOT PASSED**. The local Ollama adapter is real and measured, but qwen3:1.7b scored operation F1 0.030 on 55 cases and 0.000 on the held-out ten. It is suitable for failure analysis only, not a real-firm pilot.

## Gate C — founder-operated real-firm pilot

Required: participating-firm consent, approved data handling, production identity, tenant/document isolation, representative import and extraction evaluation, backup and isolated restore, monitoring, support escalation, manual fallback and permitted channel consent.

Status: **NOT PASSED**. Do not process confidential real-customer files.

## Gate D — production commercial SaaS

Required: repeatable onboarding, stronger reliability and load evidence, production integrations and approvals, lawful billing, support, incident response and customer metrics.

Status: **NOT PASSED**.

## External actions still requiring separate authorization

Purchases, recurring hosting charges, DNS edits, public deployment, live Meta sends, customer email, payment activation and confidential real-customer data processing.
