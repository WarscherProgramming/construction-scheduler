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


DATABASE_URL = require_environment_variable("DATABASE_URL")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60

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


_default_attachment_root = (
    Path(__file__).resolve().parents[2] / ".attachment_storage"
)
_configured_attachment_root = os.getenv(
    "ATTACHMENT_LOCAL_STORAGE_ROOT",
    "",
).strip()

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
)
