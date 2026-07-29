
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    require_secret_key,
)
from app.core.identity import normalize_email, validate_password_byte_length
from app.db.database import get_db
from app.models.user import User

SECRET_KEY = require_secret_key()
DUMMY_PASSWORD_HASH = (
    "$2b$12$6Z8eDHHCQ43/DsNhA70b..ejjg8CDstW6gxhgWFcD..Lzn9APZ5fO"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):
    validate_password_byte_length(password)
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    try:
        validate_password_byte_length(plain_password)
    except ValueError:
        pwd_context.verify("invalid-overlong-password", DUMMY_PASSWORD_HASH)
        return False

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "aud": JWT_AUDIENCE,
        "exp": expire,
        "iat": issued_at,
        "iss": JWT_ISSUER,
        "jti": uuid4().hex,
        "type": "access",
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={
                "require_aud": True,
                "require_exp": True,
                "require_iat": True,
                "require_iss": True,
                "require_jti": True,
                "require_sub": True,
            },
        )

    except (JWTError, TypeError, ValueError) as error:
        raise _authentication_error() from error

    user_id = payload.get("user_id")
    subject = payload.get("sub")
    issued_at = payload.get("iat")
    token_id = payload.get("jti")
    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
        or not isinstance(subject, str)
        or isinstance(issued_at, bool)
        or not isinstance(issued_at, (int, float))
        or issued_at <= 0
        or issued_at > datetime.now(timezone.utc).timestamp() + 30
        or not isinstance(token_id, str)
        or len(token_id) != 32
        or any(character not in "0123456789abcdef" for character in token_id)
        or payload.get("type") != "access"
    ):
        raise _authentication_error()

    try:
        normalized_subject = normalize_email(subject)
    except ValueError as error:
        raise _authentication_error() from error
    if subject != normalized_subject:
        raise _authentication_error()

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.email != normalized_subject:
        raise _authentication_error()

    return {
        "id": user.id,
        "email": user.email,
    }
