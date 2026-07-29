from pydantic import BaseModel, Field, field_validator

from app.core.identity import normalize_email, validate_password_byte_length


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_identity(cls, value):
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_limit(cls, value):
        return validate_password_byte_length(value)


class UserResponse(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
