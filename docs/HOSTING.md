# Host the QShift staff pilot

This setup runs the fictional-data staff pilot on AWS Lightsail in Mumbai (`ap-south-1`). Caddy serves the signed WhatsApp webhook over HTTPS. The review screen is reachable through SSH by an operator, and a separate worker handles replies to the enrolled tester. Both use a private managed PostgreSQL database. The application keeps its demo identities, offline extraction fixtures and 24-hour pilot enrollment.

## Hosting bill

| Resource | Published base price | Configuration |
|---|---:|---|
| Lightsail Linux instance | $12/month | 2 GB RAM and an attached static IPv4 address |
| Lightsail PostgreSQL | $30/month | Standard plan with encryption at rest, private mode |
| Total | $42/month | Before taxes, domain registration if needed, optional snapshots and overages |

The managed database price is for the encrypted tier. Confirm the total in the AWS console before creating resources. Use an existing domain if available. [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/) · [Lightsail regions](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html)

## 1. Create the host and database

1. In the QShift owner's Lightsail account, select **Mumbai**, create an **Ubuntu 24.04 LTS** instance on the 2 GB Linux plan and attach a static IPv4 address.
2. Allow inbound TCP 80 and 443. Limit TCP 22 to the operator's IP address. Keep 8000, 8765 and 5432 closed to the internet. Configure the IPv6 firewall as well if IPv6 is enabled. [Lightsail firewall docs](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html)
3. Create a PostgreSQL database on the encrypted standard plan in **Mumbai** and leave public mode off. PostgreSQL 16 was used in the local container rehearsal. Verify that automated backups are available. [Create a Lightsail database](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-a-database.html) · [Private mode and backups](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-databases.html)
4. At your domain provider, point a DNS `A` record such as `wa.your-domain.com` at the static IPv4 address. Caddy obtains and renews the public TLS certificate. [Caddy Automatic HTTPS](https://caddyserver.com/docs/automatic-https)
5. Copy the repository source to the instance over SSH or clone your private repository. Install Docker Engine and Docker Compose v2.30 or later. Use Docker Engine 28 or later so a port published to loopback stays restricted to the host. [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) · [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)

## 2. Configure secrets on the server

From the repository root on the server, create the private files from the examples:

```sh
umask 077
for name in db webhook worker review; do
  cp "deploy/$name.env.example" "deploy/$name.env"
done
printf '%s\n' 'QSHIFT_DOMAIN=wa.your-domain.com' 'QSHIFT_IMAGE_TAG=pilot-1' > .env
curl -fsS https://truststore.pki.rds.amazonaws.com/ap-south-1/ap-south-1-bundle.pem -o deploy/rds-ca.pem
chmod 644 deploy/rds-ca.pem
```

Edit `.env` with the actual hostname. From the server, connect to PostgreSQL as the database administrator using certificate verification. Create the `qshift` login and `qshift_pilot` database, owned by `qshift`. In `psql`, `\password qshift` prompts for the password without putting it in command history. Use the new application login in `deploy/db.env` and keep `sslmode=verify-full`. Encode any reserved URL characters in its password. [Lightsail PostgreSQL TLS](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-connecting-to-postgres-database-using-ssl.html)

```sql
CREATE ROLE qshift LOGIN;
\password qshift
CREATE DATABASE qshift_pilot OWNER qshift;
```

Enter the staff test number identifiers and Meta app secret in `deploy/webhook.env`. Generate distinct random values with `openssl rand -hex 32` for the webhook verify token and `QSHIFT_APPROVAL_SECRET` in `deploy/review.env`. Keep `QSHIFT_WHATSAPP_RECEIVE_ENABLED` and `QSHIFT_WHATSAPP_SEND_ENABLED` off during preparation. The Meta access token belongs only in `deploy/worker.env`. Keep the `.env` files private and out of Git, chat and shared logs.

## 3. Initialize and verify the connection

```sh
docker compose --profile '*' config --quiet
docker compose build webhook
docker compose run --rm --no-deps webhook alembic upgrade head
docker compose run --rm --no-deps webhook python -m qshift.whatsapp_pilot seed
```

After the operator authorizes the public callback, set `QSHIFT_WHATSAPP_RECEIVE_ENABLED=true` and start `docker compose up -d --wait edge`. Test the public hostname with a browser or `curl`. `/` and `/healthz` should return 404. `/webhooks/whatsapp` without a verify token should return 403. The review UI and database stay private.

In the Meta dashboard, configure `https://wa.your-domain.com/webhooks/whatsapp` with your private verify token. Subscribe to `messages` and confirm your one tester is on the test-number recipient list. Once they have opted in and know how to reach a human, record the opt-in reference and have them send `projects` to the test number. [Meta webhook guide](https://whatsappbusiness.com/blog/how-to-use-webhooks-from-whatsapp-business-api/)

```sh
docker compose exec webhook python -m qshift.whatsapp_pilot consent --reference CONSENT-001
docker compose exec webhook python -m qshift.whatsapp_delivery preview
```

## 4. Check one reply and review the draft

After authorizing a test reply, enter the current Meta test access token and Graph API version in `deploy/worker.env` and set `QSHIFT_WHATSAPP_SEND_ENABLED=true`. Try one reply with the worker still off:

```sh
docker compose run --rm --no-deps worker python -m qshift.whatsapp_delivery run --once
```

Confirm it arrived on the enrolled phone. For the rest of the session, start the worker with `docker compose up -d worker`. Have the tester send `use project-sharma`, describe the quartz and false ceiling change from [the pilot script](META_FEASIBILITY.md#staff-replies) and pick the offered Calacatta SKU. The expected draft is **₹2,43,200**.

On the host, start `docker compose up -d review`. On the operator's computer, open a private SSH connection and then visit [the forwarded review screen](http://127.0.0.1:8000/):

```sh
ssh -N -L 127.0.0.1:8000:127.0.0.1:8000 ubuntu@YOUR_STATIC_IP
```

Type `status` for Sharma Residence, switch to the Approver role, approve the exact draft and download the PDF from the review screen.

## Operations

- Stop replies with `docker compose --profile delivery stop worker`. Take down the webhook with `docker compose stop edge webhook`. The tester can also send `STOP`, and consent expires after 24 hours.
- Check `docker compose ps` and `docker compose logs --tail=50 edge webhook`. Container logs rotate. Caddy and Uvicorn omit request access logs, and Caddy removes request URIs and headers from its diagnostic log fields.
- Before updating, confirm a restore point and retain the previous image tag. Stop the worker, review and edge, build a new image tag, run migrations once, then restart the webhook and confirm Meta verification before bringing the worker back. Restore the database separately if a failed migration is incompatible with the earlier image.
- Test a restore into a separate private database before relying on backups. Keep the restored instance disconnected from Meta to avoid sending queued pilot replies.
- End the pilot by stopping the worker, removing the Meta callback and clearing retained pilot data, including retained copies, according to the participant's agreement. AWS charges can continue for stopped resources. Delete approved disposable resources when finished. [Lightsail billing](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html)

## Before customer use

The hosted build uses one Meta test number, one enrolled tester and seeded demo credentials. Customer launch requires production eligibility for the QShift workflow and number, individual accounts with tenant-scoped access, real extraction evaluated on representative data, customer consent and retention controls, and operational checks for delivery, recovery and support. Use a separate environment for the customer launch.
