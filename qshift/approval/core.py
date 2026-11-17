"""Signed, expiring approval tokens bound to one user and exact draft content."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(
    draft_id: str,
    content_sha256: str,
    approver_id: str,
    secret: bytes,
    lifetime: timedelta = timedelta(minutes=10),
    now: datetime | None = None,
) -> tuple[str, datetime]:
    issued_at = now or datetime.now(UTC)
    expiry = issued_at + lifetime
    nonce = secrets.token_urlsafe(24)
    payload = f"{draft_id}:{content_sha256}:{approver_id}:{int(expiry.timestamp())}:{nonce}"
    signature = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}", expiry


def validate_token(token: str, secret: bytes, now: datetime | None = None) -> dict[str, str]:
    pieces = token.split(":")
    if len(pieces) != 6:
        raise ValueError("Malformed approval token")
    draft_id, digest, approver_id, expiry_s, nonce, signature = pieces
    payload = ":".join(pieces[:-1])
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid approval token signature")
    current = now or datetime.now(UTC)
    expiry = datetime.fromtimestamp(int(expiry_s), UTC)
    if expiry < current:
        raise ValueError("Approval token expired")
    return {
        "draft_id": draft_id,
        "content_sha256": digest,
        "approver_id": approver_id,
        "expires_at": expiry.isoformat(),
        "nonce": nonce,
    }
