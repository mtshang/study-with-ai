import unicodedata
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, field_serializer

def normalize_username(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()

class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        value = normalize_username(value)
        if not 3 <= len(value) <= 64 or len(value.casefold()) > 191:
            raise ValueError("用户名需为 3–64 个字符")
        if any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("用户名不能包含控制字符或不可见格式字符")
        return value

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_date(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat()
