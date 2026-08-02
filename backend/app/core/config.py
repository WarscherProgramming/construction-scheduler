import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

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


def positive_integer_environment_variable(
    name: str,
    default: int,
    *,
    maximum: int | None = None,
) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error

    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be at most {maximum}")

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


def allowed_origins_environment_variable() -> tuple[str, ...]:
    configured = os.getenv(
        "ALLOWED_ORIGINS",
        (
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "https://construction-scheduler-eight.vercel.app"
        ),
    )
    origins = []
    for value in configured.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*" or origin.lower() == "null":
            raise RuntimeError(
                "ALLOWED_ORIGINS cannot contain wildcard or null origins"
            )

        parsed = urlsplit(origin)
        try:
            parsed.port
        except ValueError as error:
            raise RuntimeError(
                "ALLOWED_ORIGINS contains an invalid origin"
            ) from error
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(
                "ALLOWED_ORIGINS must contain absolute HTTP(S) origins"
            )

        normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if normalized not in origins:
            origins.append(normalized)

    return tuple(origins)


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
if APP_ENV not in {"development", "test", "production"}:
    raise RuntimeError("APP_ENV must be development, test, or production")

APP_DEBUG = boolean_environment_variable("APP_DEBUG", False)
DATABASE_URL = require_environment_variable("DATABASE_URL")
ALGORITHM = "HS256"
ALLOWED_ORIGINS = allowed_origins_environment_variable()

ACCESS_TOKEN_EXPIRE_MINUTES = positive_integer_environment_variable(
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    15,
    maximum=60,
)
REFRESH_TOKEN_EXPIRE_DAYS = positive_integer_environment_variable(
    "REFRESH_TOKEN_EXPIRE_DAYS",
    14,
    maximum=90,
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
    maximum=10_000,
)
REFRESH_SESSION_RETENTION_DAYS = positive_integer_environment_variable(
    "REFRESH_SESSION_RETENTION_DAYS",
    30,
    maximum=365,
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


@dataclass(frozen=True)
class DocumentExtractionConfig:
    enabled: bool
    ocr_enabled: bool
    ocr_provider: str
    ocr_language: str
    max_pages: int
    ocr_max_pages: int
    max_chars_per_page: int
    max_chars_per_document: int
    embedded_text_threshold: int
    ocr_dpi: int
    ocr_max_pixels: int
    ocr_max_dimension: int
    extraction_timeout_seconds: int
    ocr_page_timeout_seconds: int
    max_attempts: int
    retry_base_seconds: int
    retry_max_seconds: int
    lease_seconds: int
    batch_size: int
    retention_days: int
    reprocess_rate_limit: int
    reprocess_rate_window_seconds: int


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
        maximum=104_857_600,
    ),
    upload_chunk_size=positive_integer_environment_variable(
        "ATTACHMENT_UPLOAD_CHUNK_SIZE",
        65_536,
        maximum=1_048_576,
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
        maximum=300,
    ),
    s3_read_timeout=positive_integer_environment_variable(
        "ATTACHMENT_S3_READ_TIMEOUT",
        60,
        maximum=300,
    ),
    s3_max_retries=positive_integer_environment_variable(
        "ATTACHMENT_S3_MAX_RETRIES",
        3,
        maximum=10,
    ),
    s3_key_prefix=normalize_attachment_key_prefix(
        optional_environment_variable("ATTACHMENT_S3_KEY_PREFIX")
    ),
    cleanup_batch_size=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_BATCH_SIZE",
        100,
        maximum=10_000,
    ),
    cleanup_max_attempts=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_MAX_ATTEMPTS",
        8,
        maximum=100,
    ),
    cleanup_retry_base_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETRY_BASE_SECONDS",
        30,
        maximum=86_400,
    ),
    cleanup_retry_max_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETRY_MAX_SECONDS",
        3600,
        maximum=86_400,
    ),
    cleanup_lease_seconds=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_LEASE_SECONDS",
        900,
        maximum=86_400,
    ),
    cleanup_retention_days=positive_integer_environment_variable(
        "ATTACHMENT_CLEANUP_RETENTION_DAYS",
        30,
        maximum=3_650,
    ),
)

_document_ocr_provider = os.getenv(
    "DOCUMENT_OCR_PROVIDER",
    "disabled",
).strip().lower()
if _document_ocr_provider not in {"disabled"}:
    raise RuntimeError("DOCUMENT_OCR_PROVIDER must be disabled")

_document_ocr_language = os.getenv(
    "DOCUMENT_OCR_LANGUAGE",
    "eng",
).strip().lower()
if (
    not _document_ocr_language
    or len(_document_ocr_language) > 16
    or any(
        not (character.isalnum() or character in {"-", "_"})
        for character in _document_ocr_language
    )
):
    raise RuntimeError("DOCUMENT_OCR_LANGUAGE is invalid")

DOCUMENT_EXTRACTION_CONFIG = DocumentExtractionConfig(
    enabled=boolean_environment_variable(
        "DOCUMENT_EXTRACTION_ENABLED",
        True,
    ),
    ocr_enabled=boolean_environment_variable(
        "DOCUMENT_OCR_ENABLED",
        False,
    ),
    ocr_provider=_document_ocr_provider,
    ocr_language=_document_ocr_language,
    max_pages=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_MAX_PAGES",
        500,
        maximum=2_000,
    ),
    ocr_max_pages=positive_integer_environment_variable(
        "DOCUMENT_OCR_MAX_PAGES",
        50,
        maximum=500,
    ),
    max_chars_per_page=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_MAX_CHARS_PER_PAGE",
        100_000,
        maximum=1_000_000,
    ),
    max_chars_per_document=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_MAX_CHARS_PER_DOCUMENT",
        2_000_000,
        maximum=10_000_000,
    ),
    embedded_text_threshold=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_EMBEDDED_TEXT_THRESHOLD",
        20,
        maximum=1_000,
    ),
    ocr_dpi=positive_integer_environment_variable(
        "DOCUMENT_OCR_DPI",
        200,
        maximum=300,
    ),
    ocr_max_pixels=positive_integer_environment_variable(
        "DOCUMENT_OCR_MAX_PIXELS",
        40_000_000,
        maximum=100_000_000,
    ),
    ocr_max_dimension=positive_integer_environment_variable(
        "DOCUMENT_OCR_MAX_DIMENSION",
        12_000,
        maximum=20_000,
    ),
    extraction_timeout_seconds=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_TIMEOUT_SECONDS",
        120,
        maximum=900,
    ),
    ocr_page_timeout_seconds=positive_integer_environment_variable(
        "DOCUMENT_OCR_PAGE_TIMEOUT_SECONDS",
        30,
        maximum=300,
    ),
    max_attempts=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_MAX_ATTEMPTS",
        3,
        maximum=10,
    ),
    retry_base_seconds=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_RETRY_BASE_SECONDS",
        60,
        maximum=86_400,
    ),
    retry_max_seconds=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_RETRY_MAX_SECONDS",
        3_600,
        maximum=86_400,
    ),
    lease_seconds=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_LEASE_SECONDS",
        900,
        maximum=86_400,
    ),
    batch_size=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_BATCH_SIZE",
        10,
        maximum=100,
    ),
    retention_days=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_RETENTION_DAYS",
        30,
        maximum=3_650,
    ),
    reprocess_rate_limit=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_REPROCESS_RATE_LIMIT",
        5,
        maximum=100,
    ),
    reprocess_rate_window_seconds=positive_integer_environment_variable(
        "DOCUMENT_EXTRACTION_REPROCESS_RATE_WINDOW_SECONDS",
        3_600,
        maximum=86_400,
    ),
)

if DOCUMENT_EXTRACTION_CONFIG.ocr_enabled:
    raise RuntimeError(
        "DOCUMENT_OCR_ENABLED requires a deployable OCR provider; "
        "this release supports DOCUMENT_OCR_PROVIDER=disabled"
    )
if (
    DOCUMENT_EXTRACTION_CONFIG.ocr_max_pages
    > DOCUMENT_EXTRACTION_CONFIG.max_pages
):
    raise RuntimeError(
        "DOCUMENT_OCR_MAX_PAGES cannot exceed "
        "DOCUMENT_EXTRACTION_MAX_PAGES"
    )
if (
    DOCUMENT_EXTRACTION_CONFIG.retry_base_seconds
    > DOCUMENT_EXTRACTION_CONFIG.retry_max_seconds
):
    raise RuntimeError(
        "DOCUMENT_EXTRACTION_RETRY_BASE_SECONDS cannot exceed "
        "DOCUMENT_EXTRACTION_RETRY_MAX_SECONDS"
    )

MAX_REQUEST_BODY_BYTES = positive_integer_environment_variable(
    "MAX_REQUEST_BODY_BYTES",
    ATTACHMENT_CONFIG.max_upload_size + 1_048_576,
    maximum=134_217_728,
)
AUTH_LOGIN_RATE_LIMIT = positive_integer_environment_variable(
    "AUTH_LOGIN_RATE_LIMIT",
    5,
    maximum=100,
)
AUTH_LOGIN_RATE_WINDOW_SECONDS = positive_integer_environment_variable(
    "AUTH_LOGIN_RATE_WINDOW_SECONDS",
    300,
    maximum=86_400,
)
AUTH_REGISTER_RATE_LIMIT = positive_integer_environment_variable(
    "AUTH_REGISTER_RATE_LIMIT",
    3,
    maximum=100,
)
AUTH_REGISTER_RATE_WINDOW_SECONDS = positive_integer_environment_variable(
    "AUTH_REGISTER_RATE_WINDOW_SECONDS",
    3600,
    maximum=604_800,
)
AUTH_RATE_LIMIT_MAX_ENTRIES = positive_integer_environment_variable(
    "AUTH_RATE_LIMIT_MAX_ENTRIES",
    10_000,
    maximum=1_000_000,
)

if MAX_REQUEST_BODY_BYTES <= ATTACHMENT_CONFIG.max_upload_size:
    raise RuntimeError(
        "MAX_REQUEST_BODY_BYTES must exceed ATTACHMENT_MAX_UPLOAD_SIZE"
    )

if APP_ENV == "production":
    if APP_DEBUG:
        raise RuntimeError("APP_DEBUG must be false in production")
    if not ALLOWED_ORIGINS:
        raise RuntimeError("ALLOWED_ORIGINS is required in production")
    if any(not origin.startswith("https://") for origin in ALLOWED_ORIGINS):
        raise RuntimeError(
            "Production ALLOWED_ORIGINS must use HTTPS"
        )
    if not COOKIE_SECURE:
        raise RuntimeError("COOKIE_SECURE must be true in production")
