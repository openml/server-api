"""Pydantic schemas for run-related endpoints."""

from pydantic import BaseModel, Field


class TraceIteration(BaseModel):
    """A single trace iteration for a run."""

    repeat: int
    fold: int
    iteration: int
    setup_string: str | None
    evaluation: float | None
    selected: bool


class RunTrace(BaseModel):
    """Trace data for a run."""

    run_id: int = Field(serialization_alias="run_id")
    trace: list[TraceIteration]
