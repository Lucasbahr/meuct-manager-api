from pydantic import BaseModel, EmailStr, field_validator
from app.core.email_utils import normalize_email


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email_field(cls, v: EmailStr):
        return normalize_email(str(v))


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email_field(cls, v: str):
        return normalize_email(v)
