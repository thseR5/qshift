# Incident and recovery

## Immediate actions

1. Disable live send and model flags; leave webhook acknowledgement on if required by Meta.
2. Preserve redacted audit IDs, provider IDs and timestamps; never copy secrets or customer files
   into tickets.
3. Identify affected firm/project/version, revoke the enrollment or token, and stop retries.
4. Notify the owner through the documented support channel and record the incident decision.

## Recovery

Restore PostgreSQL into an isolated staging database, verify migrations and quote hashes, run
fictional replay tests, then re-enable processing in stages. A message transport timeout is
`needs_review`, not proof of failure or permission to duplicate-send. Export/delete requests and
retention decisions require the firm's approved process and appropriate professional review.
