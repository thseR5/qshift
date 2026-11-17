"""Provision fictional studios and authenticate isolated studio sessions."""

import argparse
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from qshift.db import SessionLocal
from qshift.models import Firm, StudioCredential, StudioProfile, StudioSession, User, now_utc
from qshift.services import audit, hash_text, uid

COOKIE = "qshift_studio"
SESSION_SECONDS = 8 * 60 * 60
HANDLE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,63}$")


def handle(value: str) -> str:
    normalized = value.strip().lower()
    if not HANDLE.fullmatch(normalized):
        raise ValueError("Use 2–64 lowercase letters, numbers, dots or hyphens.")
    return normalized


def derive(password: str, salt: bytes) -> str:
    return hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64 * 1024 * 1024
    ).hex()


def provision(
    session: Session,
    slug: str,
    username: str,
    name: str,
    password: str,
    *,
    role: str = "OWNER",
    firm_name: str | None = None,
) -> str:
    slug, username = handle(slug), handle(username)
    if not 14 <= len(password) <= 128:
        raise ValueError("Use a password with 14–128 characters.")
    if role not in {"OWNER", "DESIGNER", "APPROVER"}:
        raise ValueError("Unknown role.")
    profile = session.get(StudioProfile, slug)
    if firm_name is not None:
        if profile is not None:
            raise ValueError("That studio already exists.")
        firm_id = uid()
        session.add(Firm(id=firm_id, name=firm_name, illustrative=True))
        session.flush()
        session.add(StudioProfile(slug=slug, firm_id=firm_id))
    elif profile is not None:
        firm_id = profile.firm_id
    else:
        raise ValueError("Create the fictional studio before adding a member.")
    if session.get(StudioCredential, (firm_id, username)) is not None:
        raise ValueError("That username already belongs to this studio.")
    user = User(
        id=uid(),
        firm_id=firm_id,
        name=name,
        role=role,
        demo_token_hash=hash_text(secrets.token_urlsafe(48)),
    )
    salt = secrets.token_bytes(16)
    session.add(user)
    session.flush()
    session.add(
        StudioCredential(
            firm_id=firm_id,
            username=username,
            user_id=user.id,
            password_hash=salt.hex() + ":" + derive(password, salt),
        )
    )
    audit(session, firm_id, user.id, "STUDIO_MEMBER_PROVISIONED", user.id, role)
    session.commit()
    return firm_id


def in_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def login(session: Session, slug: str, username: str, password: str) -> str | None:
    try:
        slug, username = handle(slug), handle(username)
    except ValueError:
        return None
    profile = session.get(StudioProfile, slug)
    account = (
        session.get(StudioCredential, (profile.firm_id, username), with_for_update=True)
        if profile
        else None
    )
    now = now_utc()
    if account and account.locked_until and in_utc(account.locked_until) > now:
        return None
    if account is None:
        derive(password, b"\0" * 16)
        return None
    salt, digest = account.password_hash.split(":")
    if not hmac.compare_digest(derive(password, bytes.fromhex(salt)), digest):
        account.failed_attempts += 1
        if account.failed_attempts >= 5:
            account.locked_until = now + timedelta(minutes=15)
            account.failed_attempts = 0
        session.commit()
        return None
    account.failed_attempts = 0
    account.locked_until = None
    token = secrets.token_urlsafe(32)
    session.add(
        StudioSession(
            firm_id=account.firm_id,
            token_hash=hash_text(token),
            user_id=account.user_id,
            expires_at=now + timedelta(seconds=SESSION_SECONDS),
        )
    )
    session.commit()
    return account.firm_id + "." + token


def get_session_record(session: Session, cookie: str | None) -> StudioSession | None:
    if not cookie or not re.fullmatch(r"[a-f0-9-]{36}\.[A-Za-z0-9_-]{43}", cookie):
        return None
    firm_id, token = cookie.split(".")
    return session.get(StudioSession, (firm_id, hash_text(token)))


def session_user(session: Session, cookie: str | None) -> User | None:
    record = get_session_record(session, cookie)
    if record is None or in_utc(record.expires_at) <= now_utc():
        return None
    return session.scalar(
        select(User).where(User.id == record.user_id, User.firm_id == record.firm_id)
    )


def logout(session: Session, cookie: str | None) -> None:
    record = get_session_record(session, cookie)
    if record is not None:
        session.delete(record)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studio", help="Fictional studio slug")
    parser.add_argument("username", help="Fictional username")
    parser.add_argument("--name", required=True, help="Fictional display name")
    parser.add_argument("--firm-name", help="Create a fictional studio with this name")
    parser.add_argument("--role", choices=["OWNER", "DESIGNER", "APPROVER"], default="OWNER")
    args = parser.parse_args()
    password = getpass("New local studio password: ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords did not match.")
    with SessionLocal() as session:
        try:
            provision(
                session,
                args.studio,
                args.username,
                args.name,
                password,
                role=args.role,
                firm_name=args.firm_name,
            )
        except ValueError as exc:
            parser.error(str(exc))
    print("Fictional studio member provisioned.")


if __name__ == "__main__":
    main()
