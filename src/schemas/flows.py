from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.types import Identifier, TagString


class Parameter(BaseModel):
    name: str
    default_value: Any
    data_type: str
    description: str


class Flow(BaseModel):
    id: Identifier
    uploader_id: Identifier | None = Field(serialization_alias="uploader")
    name: str = Field(max_length=1024)
    class_name: str | None = Field(max_length=256)
    version: int
    external_version: str = Field(max_length=128)
    description: str | None
    upload_date: datetime
    language: str | None = Field(max_length=128)
    dependencies: str | None
    parameter: list[Parameter]
    subflows: list[Subflow]
    tag: list[TagString]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Subflow(BaseModel):
    alias: str | None = Field(alias="identifier")
    flow: Flow
