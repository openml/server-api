from typing import Literal

from pydantic import BaseModel


class TraceIteration(BaseModel):
    repeat: str
    fold: str
    iteration: str
    setup_string: str
    evaluation: str
    selected: Literal["true", "false"]


class RunTrace(BaseModel):
    run_id: str
    trace_iteration: list[TraceIteration]


# Wraps RunTrace in {"trace": {...}} to match PHP API response structure.
class RunTraceResponse(BaseModel):
    trace: RunTrace
