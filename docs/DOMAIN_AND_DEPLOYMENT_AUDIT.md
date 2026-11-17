# Qshift domain and deployment audit

Read-only check performed on 2026-11-17 from the local development environment.

## Observed

- `qshift.in` returned one A record: `192.64.119.99`.
- An HTTPS `HEAD` request to `https://qshift.in` timed out after 10 seconds.

## Not established by this check

- Registrar ownership or account access.
- Whether the returned address belongs to a Qshift-controlled host.
- A valid TLS certificate, production application, health endpoint or deployment provenance.
- DNS records for a future API/webhook host.

No DNS, registrar, hosting or certificate changes were made. The local `/site` route remains the only verified public-entry implementation in this repository, and it is not deployed by this project.

## Safe next gate

Before connecting any production identity or WhatsApp webhook, the founder must separately authorize a hosting plan, verify domain control, deploy behind HTTPS, test a health endpoint, configure secrets outside source control and complete a production Meta review. Until then, keep using the clearly simulated local workflow.
