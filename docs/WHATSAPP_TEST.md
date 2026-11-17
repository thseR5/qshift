# QShift first-quote WhatsApp test

Use Meta's QShift test number and one consenting, verified recipient. Agree the
retention period with the tester and tell them Meta and Cloudflare relay the test
messages, QShift stores the fictional brief and draft locally, and `STOP` ends the
test. The test uses one wardrobe, a seeded verified rate and a local Qwen model.

1. In the QShift Meta app, open **Use cases → Connect on WhatsApp → Step 1. Try it out**.
   Under **Recipient → Manage phone number list**, add the tester and complete Meta verification.
2. From the repo, run `make whatsapp-test` in your own Terminal. It uses the local
   Ollama and Cloudflare binaries if available, or an already running local Ollama
   with `qwen3:1.7b` and `cloudflared` on PATH. The app secret, tester number and
   temporary access token are entered at hidden prompts. The script makes a private
   SQLite database and starts the webhook on loopback behind a temporary HTTPS URL.
3. Open **Step 2. Production setup → Configure Webhooks**. Use the callback URL and
   verify token shown in Terminal. Choose **Verify and save** and subscribe to
   `messages` for the test account. Finish the Terminal prompts with the
   temporary test token, Graph API version, and an opaque consent reference.
4. The tester sends “Need a wardrobe for the guest bedroom, white laminate, 6 ft wide.”
   When QShift asks the height, reply “7 feet”. The expected fictional total is ₹52,500.
5. In Terminal, enter `review`. The local operator reviews the item, area, rate
   and total, then enters `approve <hash>` using the exact hash displayed.
   Enter `send <hash>` to request PDF delivery. The recipient must confirm the
   watermarked document appeared in the same WhatsApp chat. An API acceptance
   is recorded separately from phone receipt.
6. Enter `stop` to close local pilot processes and the temporary tunnel. Remove
   the temporary callback from Meta and apply the agreed retention period to
   the private pilot database. The temporary token will expire.

The public service serves only the signed WhatsApp callback. For new local
pilots, the callback stores signed incoming text in the migrated database and
returns before extraction. The worker resumes queued text after restart, leaves
it queued if the local model is unavailable, and clears it from the inbox after
processing. Sending `STOP` clears unprocessed text and suppresses pending replies.
Running services from before migration `0009_pilot_inbox` require a coordinated
restart. A separate pilot database avoids changing an active rehearsal.

Document delivery
requires the exact approved first version, the enrolled recipient, active consent
and a recent inbound message. It records one attempt before contacting Meta and
leaves timeouts and rejected requests for review. The local Terminal is the
approval surface for this pilot. The workspace simulator remains separate.

[Meta WhatsApp Cloud API](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api) ·
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
