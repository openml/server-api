from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RunUploadResponse(BaseModel):
    """Response returned by POST /runs after a successful upload."""

    run_id: int = Field(
        serialization_alias="run_id",
        json_schema_extra={"example": 42},
    )


class RunEvaluationResult(BaseModel):
    """A single per-fold or global evaluation measure for a run."""

    function: str = Field(
        json_schema_extra={"example": "predictive_accuracy"},
        description="Name of the evaluation measure (math_function.name in the DB).",
    )
    value: float | None = Field(
        json_schema_extra={"example": 0.9312},
    )
    # Per-fold values are stored as a JSON array string in the DB.
    per_fold: list[float] | None = Field(
        default=None,
        json_schema_extra={"example": [0.92, 0.94, 0.93]},
    )


class RunDetail(BaseModel):
    """Full metadata for a single run, returned by GET /runs/{run_id}."""

    id_: int = Field(serialization_alias="run_id", json_schema_extra={"example": 42})
    task_id: int = Field(json_schema_extra={"example": 59})
    flow_id: int = Field(json_schema_extra={"example": 1})
    uploader: int = Field(json_schema_extra={"example": 16})
    upload_time: datetime = Field(
        json_schema_extra={"example": "2024-01-15T10:30:00"},
    )
    setup_string: str | None = Field(
        default=None,
        json_schema_extra={"example": "weka.classifiers.trees.J48 -C 0.25 -M 2"},
    )
    tags: list[str] = Field(default_factory=list)
    evaluations: list[RunEvaluationResult] = Field(default_factory=list)
