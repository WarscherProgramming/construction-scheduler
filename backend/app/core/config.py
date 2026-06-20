import os

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
