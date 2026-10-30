from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

class ConfigUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision: str = Field(min_length=64,max_length=64)
    channel: Literal['chat','vision','embedding']
    base_url: str = Field(max_length=500)
    model: str = Field(max_length=120)
    api_key: SecretStr | None = None
    clear_key: bool = False
    trust_url: bool | None = None
    permission: Literal['manual','assisted','full'] | None = None

class RunInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id: UUID
    prompt: str = Field(min_length=1,max_length=12000)
    @field_validator('prompt')
    @classmethod
    def clean(cls,value):
        if not value.strip(): raise ValueError('Empty message')
        return value.strip()

class ProposalDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    approve: bool
