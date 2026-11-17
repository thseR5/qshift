# AWS staging deployment runbook

This is a gated runbook, not a deployment record. No resource is created by reading it.

1. Confirm account, region, credits/expiry, plan and approved monthly ceiling in Billing.
2. Create a least-privilege deployment role and secrets in Secrets Manager; never place Meta or
   AWS credentials in Git or `.env` committed files.
3. Build the pinned Python image, run `alembic upgrade head` against private PostgreSQL, and
   start FastAPI plus the durable worker with a health check.
4. Store documents/PDFs in a private S3 bucket with SSE-KMS, block public access, lifecycle
   deletion and tenant-prefixed object keys.
5. Put HTTPS/ACM in front of the webhook, enforce signature validation and redact logs.
6. Configure SQS only when the database inbox is insufficient; add a dead-letter queue and
   bounded visibility timeout.
7. Enable CloudWatch alarms for errors, queue depth, model failures, delivery failures and the
   approved budget ceiling. A budget alert is not a hard spend limit.
8. Run fictional webhook, migration, backup/restore and rollback tests. Only then request live
   Meta test-number authorization.

Rollback: disable external-send flags, stop workers, restore the last verified database backup,
and keep the webhook in acknowledgement-only mode until reviewed.
