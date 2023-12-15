from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field


class Parameter(BaseModel):
    name: str
    default_value: Any
    data_type: str
    description: str


class Flow(BaseModel):
    id_: int = Field(serialization_alias="id")
    uploader: int | None
    name: str = Field(max_length=1024)
    class_name: str | None = Field(max_length=256)
    version: int
    external_version: str = Field(max_length=128)
    description: str | None
    upload_date: datetime
    language: str | None = Field(max_length=128)
    dependencies: str | None
    parameter: list[Parameter]
    subflows: list[Self]
    tag: list[str]

    model_config = ConfigDict(arbitrary_types_allowed=True)
