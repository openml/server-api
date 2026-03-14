"""Pydantic schemas for run-related endpoints."""

from pydantic import BaseModel


class TraceIteration(BaseModel):
    """A single trace iteration for a run."""

    repeat: int
    fold: int
    iteration: int
    setup_string: str | None
    evaluation: float | None
    selected: str


class RunTrace(BaseModel):
    """Trace data for a run."""

    run_id: int
    trace: list[TraceIteration]
