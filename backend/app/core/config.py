import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def require_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"Required environment variable {name} is not set")

    return value.strip()


def require_secret_key() -> str:
    value = require_environment_variable("SECRET_KEY")
    normalized = value.lower()

    placeholder_markers = ("change-me", "changeme", "replace-with")
    if len(value) < 32 or any(
        marker in normalized for marker in placeholder_markers
    ):
        raise RuntimeError(
            "SECRET_KEY must contain at least 32 non-placeholder characters"
        )

    return value


DATABASE_URL = require_environment_variable("DATABASE_URL")
ALGORITHM = "HS256"

ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        (
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "https://construction-scheduler-eight.vercel.app"
        ),
    ).split(",")
    if origin.strip()
)


def positive_integer_environment_variable(
    name: str,
    default: int,
) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error

    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")

    return value


def boolean_environment_variable(
    name: str,
    default: bool,
) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true or false")


def optional_environment_variable(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def validated_secret_environment_variable(
    name: str,
    *,
    fallback: str | None = None,
) -> str:
    value = optional_environment_variable(name) or fallback
    if value is None:
        raise RuntimeError(f"Required environment variable {name} is not set")

    normalized = value.lower()
    placeholder_markers = ("change-me", "changeme", "replace-with")
    if len(value) < 32 or any(
        marker in normalized for marker in placeholder_markers
    ):
        raise RuntimeError(
            f"{name} must contain at least 32 non-placeholder characters"
        )
    return value


ACCESS_TOKEN_EXPIRE_MINUTES = positive_integer_environment_variable(
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    15,
)
REFRESH_TOKEN_EXPIRE_DAYS = positive_integer_environment_variable(
    "REFRESH_TOKEN_EXPIRE_DAYS",
    14,
)
JWT_ISSUER = os.getenv("JWT_ISSUER", "fieldflow-api").strip()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "fieldflow-web").strip()
if not JWT_ISSUER or not JWT_AUDIENCE:
    raise RuntimeError("JWT_ISSUER and JWT_AUDIENCE cannot be empty")

REFRESH_TOKEN_SECRET = validated_secret_environment_variable(
    "REFRESH_TOKEN_SECRET",
    fallback=require_secret_key(),
)
REFRESH_COOKIE_NAME = os.getenv(
    "REFRESH_COOKIE_NAME",
    "fieldflow_refresh",
).strip()
CSRF_COOKIE_NAME = os.getenv(
    "CSRF_COOKIE_NAME",
    "fieldflow_csrf",
).strip()
COOKIE_SECURE = boolean_environment_variable("COOKIE_SECURE", False)
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
COOKIE_PATH = os.getenv("COOKIE_PATH", "/auth").strip()
if COOKIE_SAMESITE not in {"strict", "lax", "none"}:
    raise RuntimeError("COOKIE_SAMESITE must be strict, lax, or none")
if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
if not COOKIE_PATH.startswith("/") or any(
    character.isspace() or character == ";" for character in COOKIE_PATH
):
    raise RuntimeError("COOKIE_PATH must be an absolute cookie path")
if not REFRESH_COOKIE_NAME or not CSRF_COOKIE_NAME:
    raise RuntimeError("Authentication cookie names cannot be empty")
_COOKIE_NAME_CHARACTERS = frozenset(
    "!#$%&'*+-.^_`|~"
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)
if any(
    character not in _COOKIE_NAME_CHARACTERS
    for name in (REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME)
    for character in name
):
    raise RuntimeError("Authentication cookie names contain invalid characters")
REFRESH_SESSION_CLEANUP_BATCH_SIZE = positive_integer_environment_variable(
    "REFRESH_SESSION_CLEANUP_BATCH_SIZE",
    100,
)
REFRESH_SESSION_RETENTION_DAYS = positive_integer_environment_variable(
    "REFRESH_SESSION_RETENTION_DAYS",
    30,
)


def normalize_attachment_key_prefix(value: str | None) -> str:
    normalized = str(value or "").strip().strip("/")
    if not normalized:
        return ""
    if "\\" in normalized:
        raise RuntimeError(
            "ATTACHMENT_S3_KEY_PREFIX cannot contain backslashes"
        )

    parts = [part for part in normalized.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise RuntimeError(
            "ATTACHMENT_S3_KEY_PREFIX cannot contain path traversal"
        )
    return "/".join(parts)


DEFAULT_ATTACHMENT_MIME_TYPES = frozenset(
    {
        "application/msword",
        "application/pdf",
        "application/vnd.ms-excel",
        (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        "image/heic",
        "image/heif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/csv",
        "text/plain",
    }
)


@dataclass(frozen=True)
class AttachmentConfig:
    storage_provider: str
    local_storage_root: Path
    max_upload_size: int
    upload_chunk_size: int
    permitted_mime_types: frozenset[str]
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_session_token: str | None = None
    s3_addressing_style: str = "auto"
    s3_secure_transport: bool = True
    s3_connect_timeout: int = 5
    s3_read_timeout: int = 60
    s3_max_retries: int = 3
    s3_key_prefix: str = ""
    cleanup_batch_size: int = 100
    cleanup_max_attempts: int = 8
    cleanup_retry_base_seconds: int = 30
    cleanup_retry_max_seconds: int = 3600
    cleanup_lease_seconds: int = 900
    cleanup_retention_days: int = 30


_default_attachment_root = (
    Path(__file__).resolve().parents[2] / ".attachment_storage"
)
_configured_attachment_root = os.getenv(
    "ATTACHMENT_LOCAL_STORAGE_ROOT",
    "",
).strip()
_configured_s3_endpoint = optional_environment_variable(
    "ATTACHMENT_S3_ENDPOINT_URL"
)

ATTACHMENT_CONFIG = AttachmentConfig(
    storage_provider=os.getenv(
        "ATTACHMENT_STORAGE_PROVIDER",
        "local",
    ).strip().lower(),
    local_storage_root=Path(
        _configured_attachment_root
        or _default_attachment_root
    ).expanduser().resolve(),
    max_upload_size=positive_integer_environment_variable(
        "ATTACHMENT_MAX_UPLOAD_SIZE",
        26_214_400,
    ),
    upload_chunk_size=positive_integer_environment_variable(
        "ATTACHMENT_UPLOAD_CHUNK_SIZE",
        65_536,
    ),
    permitted_mime_types=frozenset(
        mime_type.strip().lower()
        for mime_type in os.getenv(
            "ATTACHMENT_PERMITTED_MIME_TYPES",
            ",".join(sorted(DEFAULT_ATTACHMENT_MIME_TYPES)),
        ).split(",")
        if mime_type.strip()
    ),
    s3_bucket=optional_environment_variable("ATTACHMENT_S3_BUCKET"),
    s3_region=os.getenv(
        "ATTACHMENT_S3_REGION",
        "us-east-1",
    ).strip(),
    s3_endpoint_url=(
        _configured_s3_endpoint.rstrip("/")
        if _configured_s3_endpoint
        else None
    ),
    s3_access_key_id=optional_environment_variable(
        "ATTACHMENT_S3_ACCESS_KEY_ID"
    ),
    s3_secret_access_key=optional_environment_variable(
        "ATTACHMENT_S3_SECRET_ACCESS_KEY"
    ),
    s3_session_token=optional_environment_variable(
        "ATTACHMENT_S3_SESSION_TOKEN"
    ),
    s3_addressing_style=os.getenv(
        "ATTACHMENT_S3_ADDRESSING_STYLE",
        "auto",
    ).strip().lower(),
    s3_secure_transport=boolean_environment_variable(
        "ATTACHMENT_S3_SECURE_TRANSPORT",
        True,
    ),
    s3_connect_timeout=positive_integer_environment_variable(
        "ATTACHMENT_S3_CONNECT_TIMEOUT",
        5,
    ),
    s3_read_timeout=positive_integer_environment_variable(
        "ATTACHMENT_S3_READ_TIMEOUT",
        60,
    ),
    s3_max_retries=positive_integer_environment_variable(
        "ATTACHMENT_S3_MAX_RETRIES",
        3,
    ),
    s3_key_prefix=normalize_attachment_key_prefix(
        optional_environment_variable("ATTACHMENT_S3_KEY_PREFIX")
    ),
    cleanup_batch_size=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_BATCH_SIZE",
        100,
    ),
    cleanup_max_attempts=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_MAX_ATTEMPTS",
        8,
    ),
    cleanup_retry_base_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETRY_BASE_SECONDS",
        30,
    ),
    cleanup_retry_max_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETRY_MAX_SECONDS",
        3600,
    ),
    cleanup_lease_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_LEASE_SECONDS",
        900,
    ),
    cleanup_retention_days=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETENTION_DAYS",
        30,
    ),
)

MAX_REQUEST_BODY_BYTES = positive_integer_environment_variable(
    "MAX_REQUEST_BODY_BYTES",
    ATTACHMENT_CONFIG.max_upload_size + 1_048_576,
)
AUTH_LOGIN_RATE_LIMIT = positive_integer_environment_variable(
    "AUTH_LOGIN_RATE_LIMIT",
    5,
)
AUTH_LOGIN_RATE_WINDOW_SECONDS = positive_integer_environment_variable(
    "AUTH_LOGIN_RATE_WINDOW_SECONDS",
    300,
)
AUTH_REGISTER_RATE_LIMIT = positive_integer_environment_variable(
    "AUTH_REGISTER_RATE_LIMIT",
    3,
)
AUTH_REGISTER_RATE_WINDOW_SECONDS = positive_integer_environment_variable(
    "AUTH_REGISTER_RATE_WINDOW_SECONDS",
    3600,
)
AUTH_RATE_LIMIT_MAX_ENTRIES = positive_integer_environment_variable(
    "AUTH_RATE_LIMIT_MAX_ENTRIES",
    10_000,
)
