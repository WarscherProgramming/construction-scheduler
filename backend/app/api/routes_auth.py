import hmac
import logging
import secrets

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import (
    AUTH_LOGIN_RATE_LIMIT,
    AUTH_LOGIN_RATE_WINDOW_SECONDS,
    AUTH_RATE_LIMIT_MAX_ENTRIES,
    AUTH_REGISTER_RATE_LIMIT,
    AUTH_REGISTER_RATE_WINDOW_SECONDS,
    ALLOWED_ORIGINS,
    COOKIE_PATH,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    REFRESH_TOKEN_EXPIRE_DAYS,
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
from app.schemas.auth import (
    CsrfResponse,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_session import (
    RefreshSessionError,
    create_refresh_session,
    revoke_refresh_family,
    rotate_refresh_session,
)

router = APIRouter()
logger = logging.getLogger(__name__)
login_rate_limiter = InMemoryRateLimiter(
    max_entries=AUTH_RATE_LIMIT_MAX_ENTRIES,
)
register_rate_limiter = InMemoryRateLimiter(
    max_entries=AUTH_RATE_LIMIT_MAX_ENTRIES,
)
_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


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
        logger.warning("Authentication rate limit rejected a request")
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(result.retry_after)},
        )


def _new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=_COOKIE_MAX_AGE,
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=_COOKIE_MAX_AGE,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite=COOKIE_SAMESITE,
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=False,
        samesite=COOKIE_SAMESITE,
    )


def _invalid_session_response() -> JSONResponse:
    response = JSONResponse(
        status_code=401,
        content={"detail": "Invalid authentication credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    _clear_auth_cookies(response)
    return response


def _validate_csrf(
    request: Request,
    csrf_cookie: str | None,
    csrf_header: str | None,
) -> None:
    origin = request.headers.get("origin")
    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=403,
            detail="Request could not be verified",
        )
    if (
        not csrf_cookie
        or not csrf_header
        or not hmac.compare_digest(csrf_cookie, csrf_header)
    ):
        raise HTTPException(
            status_code=403,
            detail="Request could not be verified",
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
    response: Response,
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
        logger.info("Authentication login rejected: invalid_credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_token = create_refresh_session(db, existing_user)
    token = create_access_token({
        "sub": existing_user.email,
        "user_id": existing_user.id,
    })
    csrf_token = _new_csrf_token()
    _set_refresh_cookie(response, session_token.raw_token)
    _set_csrf_cookie(response, csrf_token)
    login_rate_limiter.reset(limit_key)
    logger.info("Authentication login succeeded")

    return {
        "access_token": token,
        "token_type": "bearer",
        "csrf_token": csrf_token,
        "user": {
            "id": existing_user.id,
            "email": existing_user.email,
        },
    }


@router.get("/auth/csrf", response_model=CsrfResponse)
def csrf(response: Response):
    csrf_token = _new_csrf_token()
    _set_csrf_cookie(response, csrf_token)
    return {"csrf_token": csrf_token}


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=REFRESH_COOKIE_NAME,
    ),
    csrf_cookie: str | None = Cookie(
        default=None,
        alias=CSRF_COOKIE_NAME,
    ),
    csrf_header: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
    db: Session = Depends(get_db),
):
    _validate_csrf(request, csrf_cookie, csrf_header)
    if not refresh_token:
        return _invalid_session_response()

    try:
        session_token = rotate_refresh_session(db, refresh_token)
    except RefreshSessionError as error:
        _clear_auth_cookies(response)
        event = (
            "refresh_token_reuse"
            if error.reason == "reuse"
            else "refresh_rejected"
        )
        logger.warning("Authentication %s", event)
        return _invalid_session_response()

    user = session_token.user
    access_token = create_access_token(
        {"sub": user.email, "user_id": user.id}
    )
    csrf_token = _new_csrf_token()
    _set_refresh_cookie(response, session_token.raw_token)
    _set_csrf_cookie(response, csrf_token)
    logger.info("Authentication refresh succeeded")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "csrf_token": csrf_token,
        "user": {"id": user.id, "email": user.email},
    }


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=REFRESH_COOKIE_NAME,
    ),
    csrf_cookie: str | None = Cookie(
        default=None,
        alias=CSRF_COOKIE_NAME,
    ),
    csrf_header: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
    db: Session = Depends(get_db),
):
    if refresh_token:
        _validate_csrf(request, csrf_cookie, csrf_header)
        revoke_refresh_family(db, refresh_token)
    _clear_auth_cookies(response)
    logger.info("Authentication logout completed")
    return {"message": "Logged out"}
