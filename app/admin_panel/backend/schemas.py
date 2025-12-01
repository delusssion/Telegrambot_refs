from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    admin_id: int = Field(..., description="Telegram ID администратора")
    password: str = Field(..., min_length=1, description="Пароль администратора")


class LoginResponse(BaseModel):
    token: str
    admin_id: int


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    username: str | None
    bank: str
    comment: str | None
    file_id: str | None
    status: str
    created_at: str


class ActionResponse(BaseModel):
    id: int
    user_id: int | None
    username: str | None
    action: str
    details: dict | None
    created_at: str

    @field_validator("created_at", mode="before")
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value
