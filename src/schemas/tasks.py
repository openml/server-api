"""Defines schemas for API responses relating to Tasks."""

from typing import Any

from pydantic import BaseModel, Field

from core.types import Identifier


class Task(BaseModel):
    """Metadata for a task."""

    id_: Identifier = Field(serialization_alias="id", json_schema_extra={"example": 59})
    name: str = Field(
        json_schema_extra={"example": "Task 59:  mfeat-pixel (Supervised Classification)"},
    )
    task_type_id: Identifier = Field(json_schema_extra={"example": 1})
    task_type: str = Field(json_schema_extra={"example": "Supervised Classification"})
    input_: list[dict[str, Any]] = Field(serialization_alias="input")
    output: list[dict[str, Any]]
    tags: list[str] = Field(default_factory=list)


class EstimationProcedure(BaseModel):
    """Description of an evaluation protocol, e.g., cross-validation."""

    id_: Identifier = Field(serialization_alias="id")
    task_type_id: Identifier
    name: str
    type_: str = Field(serialization_alias="type")
    percentage: int | None
    repeats: int | None
    folds: int | None
    stratified_sampling: bool | None
