import re


MAX_BCRYPT_PASSWORD_BYTES = 72
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+$")


def normalize_email(value: str) -> str:
    normalized = str(value).strip().lower()

    if not 3 <= len(normalized) <= 320:
        raise ValueError("Enter a valid email address")
    if not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address")

    local_part, domain = normalized.rsplit("@", 1)
    if (
        local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    ):
        raise ValueError("Enter a valid email address")

    return normalized


def validate_password_byte_length(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("Password must be 72 bytes or fewer")
    return password
