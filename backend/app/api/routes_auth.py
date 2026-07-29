
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import (
    AUTH_LOGIN_RATE_LIMIT,
    AUTH_LOGIN_RATE_WINDOW_SECONDS,
    AUTH_RATE_LIMIT_MAX_ENTRIES,
    AUTH_REGISTER_RATE_LIMIT,
    AUTH_REGISTER_RATE_WINDOW_SECONDS,
)
from app.core.identity import normalize_email
from app.models.user import User
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    verify_password,
    create_access_token,
)
from app.core.rate_limit import InMemoryRateLimiter, rate_limit_key
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse

router = APIRouter()
login_rate_limiter = InMemoryRateLimiter(
    max_entries=AUTH_RATE_LIMIT_MAX_ENTRIES,
)
register_rate_limiter = InMemoryRateLimiter(
    max_entries=AUTH_RATE_LIMIT_MAX_ENTRIES,
)


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(
    limiter: InMemoryRateLimiter,
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    result = limiter.consume(
        key,
        limit=limit,
        window_seconds=window_seconds,
    )
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(result.retry_after)},
        )


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(
    user: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    limit_key = rate_limit_key(
        "register",
        _client_host(request),
        user.email,
    )
    _enforce_rate_limit(
        register_rate_limiter,
        limit_key,
        limit=AUTH_REGISTER_RATE_LIMIT,
        window_seconds=AUTH_REGISTER_RATE_WINDOW_SECONDS,
    )

    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account"
        )

    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create account",
        ) from error
    db.refresh(new_user)
    register_rate_limiter.reset(limit_key)

    return {
        "id": new_user.id,
        "email": new_user.email
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        email = normalize_email(form_data.username)
        valid_email = True
    except ValueError:
        email = str(form_data.username).strip().lower()
        valid_email = False

    limit_key = rate_limit_key(
        "login",
        _client_host(request),
        email,
    )
    _enforce_rate_limit(
        login_rate_limiter,
        limit_key,
        limit=AUTH_LOGIN_RATE_LIMIT,
        window_seconds=AUTH_LOGIN_RATE_WINDOW_SECONDS,
    )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
        if valid_email
        else None
    )
    password_hash = (
        existing_user.hashed_password
        if existing_user is not None
        else DUMMY_PASSWORD_HASH
    )
    password_is_valid = verify_password(
        form_data.password,
        password_hash,
    )

    if existing_user is None or not password_is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": existing_user.email,
        "user_id": existing_user.id,
    })
    login_rate_limiter.reset(limit_key)

    return {
        "access_token": token,
        "token_type": "bearer"
    }
