# WhatsApp live integration boundary

The repository validates Meta-shaped signatures and verification challenges and tracks inbound
receipts, message events, outbound states and delivery-status callbacks. The current adapter is
clearly **SIMULATED** and live sends are disabled by feature flags.

Before enabling a real test number, configure a dedicated HTTPS endpoint, app secret, verify
token, account ID, phone-number ID, consent/enrollment, access token secret storage, reply-window
policy and an operator rollback. Verify the current [WhatsApp Business Platform documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview/)
and [Business Messaging Policy](https://business.whatsapp.com/policy/). Record any AI-provider
eligibility decision; do not describe Qshift as a general-purpose chatbot.

Meta acceptance is not device delivery. Reconcile `queued`, `sent`, `delivered`, `read`, `failed`
and `unknown/needs_review` status events against the tenant-scoped outbound idempotency key.
Unknown transport outcomes are not retried blindly.
