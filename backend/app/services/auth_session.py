from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import (
    REFRESH_SESSION_CLEANUP_BATCH_SIZE,
    REFRESH_SESSION_RETENTION_DAYS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_SECRET,
)
from app.models.refresh_session import RefreshSession
from app.models.user import User


REFRESH_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{64}$")
_REFRESH_DIGEST_KEY = hmac.new(
    REFRESH_TOKEN_SECRET.encode("utf-8"),
    b"fieldflow-refresh-token-v1",
    hashlib.sha256,
).digest()


class RefreshSessionError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SessionToken:
    raw_token: str
    session: RefreshSession
    user: User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def generate_refresh_token() -> str:
    token = secrets.token_urlsafe(48)
    if not REFRESH_TOKEN_PATTERN.fullmatch(token):
        raise RuntimeError("Refresh token generation produced an invalid value")
    return token


def digest_refresh_token(token: str) -> str:
    if not isinstance(token, str) or not REFRESH_TOKEN_PATTERN.fullmatch(token):
        raise RefreshSessionError("invalid")
    return hmac.new(
        _REFRESH_DIGEST_KEY,
        token.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _new_session(
    user_id: int,
    token_hash: str,
    family_id: str,
    now: datetime,
) -> RefreshSession:
    return RefreshSession(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        issued_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def cleanup_refresh_sessions(db: Session, now: datetime | None = None) -> int:
    now = now or utc_now()
    cutoff = now - timedelta(days=REFRESH_SESSION_RETENTION_DAYS)
    stale_ids = [
        row[0]
        for row in (
            db.query(RefreshSession.id)
            .filter(RefreshSession.expires_at < cutoff)
            .order_by(RefreshSession.expires_at, RefreshSession.id)
            .limit(REFRESH_SESSION_CLEANUP_BATCH_SIZE)
            .all()
        )
    ]
    if stale_ids:
        db.query(RefreshSession).filter(
            RefreshSession.id.in_(stale_ids)
        ).delete(synchronize_session=False)
    return len(stale_ids)


def create_refresh_session(db: Session, user: User) -> SessionToken:
    now = utc_now()
    raw_token = generate_refresh_token()
    session = _new_session(
        user.id,
        digest_refresh_token(raw_token),
        uuid4().hex,
        now,
    )
    db.add(session)
    cleanup_refresh_sessions(db, now)
    db.commit()
    db.refresh(session)
    return SessionToken(raw_token, session, user)


def _revoke_family(
    db: Session,
    family_id: str,
    reason: str,
    now: datetime,
) -> None:
    db.query(RefreshSession).filter(
        RefreshSession.family_id == family_id,
        RefreshSession.revoked_at.is_(None),
    ).update(
        {
            RefreshSession.revoked_at: now,
            RefreshSession.revoke_reason: reason,
            RefreshSession.last_used_at: now,
        },
        synchronize_session=False,
    )


def rotate_refresh_session(db: Session, raw_token: str) -> SessionToken:
    token_hash = digest_refresh_token(raw_token)
    now = utc_now()
    current = (
        db.query(RefreshSession)
        .filter(RefreshSession.token_hash == token_hash)
        .with_for_update()
        .first()
    )
    if current is None:
        raise RefreshSessionError("invalid")

    if current.revoked_at is not None:
        _revoke_family(db, current.family_id, "reuse_detected", now)
        db.commit()
        raise RefreshSessionError("reuse")

    if _aware(current.expires_at) <= now:
        current.revoked_at = now
        current.revoke_reason = "expired"
        current.last_used_at = now
        db.commit()
        raise RefreshSessionError("expired")

    user = db.query(User).filter(User.id == current.user_id).first()
    if user is None:
        _revoke_family(db, current.family_id, "user_missing", now)
        db.commit()
        raise RefreshSessionError("user_missing")

    replacement_token = generate_refresh_token()
    replacement = _new_session(
        current.user_id,
        digest_refresh_token(replacement_token),
        current.family_id,
        now,
    )
    db.add(replacement)
    db.flush()
    current.revoked_at = now
    current.revoke_reason = "rotated"
    current.last_used_at = now
    current.replaced_by_id = replacement.id
    cleanup_refresh_sessions(db, now)
    db.commit()
    db.refresh(replacement)
    return SessionToken(replacement_token, replacement, user)


def revoke_refresh_family(db: Session, raw_token: str) -> None:
    try:
        token_hash = digest_refresh_token(raw_token)
    except RefreshSessionError:
        return

    current = (
        db.query(RefreshSession)
        .filter(RefreshSession.token_hash == token_hash)
        .with_for_update()
        .first()
    )
    if current is None:
        return

    _revoke_family(db, current.family_id, "logout", utc_now())
    db.commit()
