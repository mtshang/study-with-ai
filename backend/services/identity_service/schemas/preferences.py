from pydantic import BaseModel,ConfigDict,Field
class DisplayPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    version: int = Field(default=0, ge=0, le=2147483647)
    fontOffset: int = Field(default=3, ge=0, le=6)
    compact: bool = False

class DisplayUpdate(DisplayPreferences):
    version: int = Field(ge=0, le=2147483646)
    fontOffset: int = Field(ge=0, le=6)
    compact: bool