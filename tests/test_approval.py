from datetime import UTC, datetime, timedelta

import pytest

from qshift.approval.core import issue_token, token_digest, validate_token


def test_token_binds_draft_hash_user_and_expiry():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token, expiry = issue_token(
        "draft-1", "a" * 64, "approver-1", b"secret", timedelta(minutes=5), now
    )
    claims = validate_token(token, b"secret", now)
    assert claims["draft_id"] == "draft-1"
    assert claims["approver_id"] == "approver-1"
    assert claims["content_sha256"] == "a" * 64
    assert expiry.isoformat() == claims["expires_at"]
    assert token_digest(token) != token_digest(token + "x")


def test_tamper_and_expiry_rejected():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token, _ = issue_token("draft-1", "a" * 64, "approver-1", b"secret", timedelta(seconds=1), now)
    with pytest.raises(ValueError, match="signature"):
        validate_token(token + "x", b"secret", now)
    with pytest.raises(ValueError, match="expired"):
        validate_token(token, b"secret", now + timedelta(seconds=2))
