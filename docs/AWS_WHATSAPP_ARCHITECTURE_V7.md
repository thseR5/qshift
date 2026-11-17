# QShift V7 AWS and WhatsApp architecture

Status: design and offline verification only. Nothing in this document deploys resources,
changes DNS, sends a WhatsApp message, or spends AWS credit.

## Customer path

`WhatsApp Business Platform -> verified HTTPS webhook -> FastAPI receiver -> durable inbox`
` -> worker -> configurable change extractor -> deterministic catalogue/pricing -> WhatsApp review`
` -> one-time server approval token -> immutable QuoteVersion -> PDF -> authorized delivery`

The customer and designer experience is WhatsApp-native. The Studio UI remains an internal
administrative/test surface and is not required for the normal path. Mode A (a dedicated
Qshift number) is the initial scope. Mode B (eligible coexistence with a firm's number) uses
the same tenant-scoped conversation, worker, approval and document services with a different
channel identity; no personal chats, groups, history, or unapproved features are assumed.

## Minimal production shape (not activated)

- **EC2**: one private application instance running FastAPI, the worker, and a reverse proxy;
  use an ALB only when availability requirements justify its fixed hourly cost.
- **RDS PostgreSQL**: Multi-AZ is a later gate; start with a private single-AZ instance and
  automated backups after a restore drill. SQLite remains the offline demo database.
- **S3**: private bucket for customer-authorized source files and generated PDFs, SSE-KMS,
  block public access, short-lived presigned URLs, lifecycle deletion, and tenant-prefixed keys.
- **SQS**: durable inbound and PDF jobs with a dead-letter queue. The current database inbox is
  the offline equivalent and remains the default until SQS is separately authorized.
- **CloudWatch**: structured logs with message/document redaction, error alarms, queue depth,
  latency, model failure and spend alarms. Never log access tokens or customer document bytes.
- **HTTPS**: ACM certificate behind ALB or a hardened reverse proxy. Meta webhook verification
  and `X-Hub-Signature-256` validation remain mandatory.
- **Bedrock adapter**: provider boundary only; model selection stays configurable and must pass
  the locked revision evaluation before use. Qwen3 1.7B is not a live-customer default.

Money, catalogue resolution, tenant authorization, versioning, approval and PDF issuance stay
inside deterministic services. AI output is an untrusted proposal envelope.

## AWS account checklist (founder must confirm in the console)

Before any deployment, record the account ID, chosen Region, Free/Paid plan, AWS credits and
expiry date from **Billing > Credits**, and the eligible Free Tier services. The CLI cannot
reliably expose every promotional credit or expiry. Run the read-only checks in:

```text
scripts/aws/account_checklist.sh
```

Then create a zero-spend budget alert (for example, alert at the approved monthly ceiling and
at 80%/100% of that ceiling), verify EC2/RDS/SQS/S3/CloudWatch/Bedrock service quotas, and set
an explicit Bedrock invocation budget. No resource should be activated until the founder has
approved the region, ceiling, and model.

## Cost worksheet

AWS prices vary by Region, instance class, storage, traffic, retention and model tokens. Use the
[AWS Pricing Calculator](https://calculator.aws/) after recording the account Region. AWS states
that EC2 and RDS are usage-based, S3 has storage/request/transfer components, and SQS charges by
request with a Free Tier allowance; see the official [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/),
[RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/),
and [SQS pricing](https://aws.amazon.com/sqs/pricing/) pages. Do not treat a rough estimate as a
quote. The calculator inputs for a tiny pilot are one EC2 instance, one small RDS instance,
single-region S3 under 10 GB, low SQS request volume, CloudWatch logs under 5 GB/month, and
Bedrock invocations only after model qualification.

## Fail-safe rules

If the model is unavailable, the worker keeps the request pending and asks for clarification;
it never prices from an unverified proposal. If a queue, budget alarm, storage policy, or
approval check fails, no document is sent. A WhatsApp `yes` is never an approval. A PDF send
attempt is committed before transport and an unknown outcome becomes `needs_review`, not an
automatic retry.

## Meta boundary

The repository's adapter is clearly **SIMULATED** and uses fictional data. Meta's current
[WhatsApp Business Platform overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview/)
documents Cloud API, webhooks and authentication; the [WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy/)
governs permitted business messaging. Live Meta callbacks, external sends, real customer data,
billing, production DNS and commercial eligibility review remain disabled until the account
owner separately authorizes and verifies them against the current terms and policies.
