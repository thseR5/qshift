# Product requirements — Qshift v0.1

Qshift helps Indian interior designers turn messy client chats into reviewable first quotes and handle later scope changes. In the first-quote simulator, a fictional client sends several messages, the local model proposes source-linked requirements, and Qshift asks for missing pricing details. It matches the agreed scope to a verified rate card, calculates the quote, and lets the designer review each line. An authorized approver releases a versioned PDF into the simulated chat.

The product is a narrow task workflow. Supported intents are project pin/list, rate-card and quotation imports, change requests, clarification, draft review, approve/reject, project change summary, version history and help. Other requests get a fixed scope response. No model calculates money, chooses an unverified price, identifies an ambiguous project, approves, or sends a client-facing quote.

The first-quote demo supports one white-laminate wardrobe and one gypsum ceiling. The separate revision simulator handles the existing fictional change scenarios. The current release uses fictional tenant data, CSV/XLSX imports, local AI or offline fixtures, SQLite persistence, deterministic pricing, approval audit and PDF output. Voice remains a transcript fixture. Production WhatsApp delivery, real customer data handling, billing, and production identity and deployment are launch work.

The client-channel rehearsal imports and verifies a fictional CSV rate card. A local webhook receives provider-shaped synthetic text events and binds the sender to that firm's project and rate card. Inbound receipts deduplicate retries. Approval records the PDF and its hash for that conversation in the same database transaction as the approved version. The simulated chat retrieves those stored bytes. The live staff test integration uses its separate authorization and message path.

