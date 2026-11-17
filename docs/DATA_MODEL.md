# Database and project-memory model

`Firm` owns `User`, `Project`, `RateCard`, `RateEntry`, `Quote`, `QuoteVersion`, `Draft`, `Approval` and append-only `AuditEvent` records. Rows carrying customer/business state include `firm_id`; foreign keys connect quote versions to a quote and rate-card snapshot. A line stores stable `line_id`, room, SKU, unit, decimal quantity as a canonical string, integer-paise rate and total, and GST basis points.

An approved version stores a content SHA-256, source rate-card version, base version, lines, change summary and author. It is never updated by the revision workflow. Project memory counts and summarizes stored operations from the prior seven days; it does not ask a language model to invent history. Demo timestamps and their resulting “this week” query are synthetic.

