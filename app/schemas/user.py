from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.core.email_utils import normalize_email


class UserCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str
    gym_id: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("gym_id", "academia_id"),
    )

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
