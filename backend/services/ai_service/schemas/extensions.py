from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, SecretStr

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ConnectorSave(Strict):
    id: UUID
    revision: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=1500)
    headers: dict[str, SecretStr] | None = None

class Revision(Strict):
    revision: int = Field(ge=1)

class ToolPolicy(Revision):
    tools: dict[str, Literal['disabled', 'read', 'write']]

class BindingSave(Strict):
    revision: int = Field(ge=0)
    enabled: list[UUID] = Field(max_length=20)

class ExtensionID(Strict):
    extension_id: UUID

class SkillFile(ExtensionID):
    path: str = Field(min_length=1, max_length=240)
    offset: int = Field(default=0, ge=0)
    revision: int = Field(ge=1)

class MCPCall(ExtensionID):
    tool: str = Field(min_length=1, max_length=128)
    arguments: dict = Field(default_factory=dict)
    revision: int = Field(ge=1)

class OutcomeReview(Strict):
    note: str = Field(min_length=1, max_length=1000)
