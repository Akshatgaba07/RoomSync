from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("name required")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    dealbreakers: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    partner_id: str | None = None
    note: str | None = Field(default=None, max_length=500)
