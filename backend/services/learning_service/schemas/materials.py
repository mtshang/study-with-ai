from pydantic import BaseModel,ConfigDict,Field,HttpUrl,field_validator
import uuid
class MaterialCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=10000)
    url: HttpUrl | None = None

    @field_validator('url')
    @classmethod
    def safe_link(cls, value):
        if value is not None and (len(str(value)) > 2048 or value.username is not None or value.password is not None):
            raise ValueError('Use an HTTP(S) address without credentials')
        return value
class MaterialEdit(MaterialCreate):
    expected_version:int=Field(ge=1)

class MaterialDelete(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:uuid.UUID
    expected_version:int=Field(ge=1)
