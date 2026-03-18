"""Endpoints for run-related data."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.runs
from core.errors import RunNotFoundError, RunTraceNotFoundError
from routers.dependencies import expdb_connection
from schemas.runs import RunTrace, TraceIteration

router = APIRouter(prefix="/run", tags=["run"])


@router.get("/trace/{run_id}")
async def get_run_trace(
    run_id: int,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> RunTrace:
    """Get trace data for a run by run ID."""
    if not await database.runs.exist(run_id, expdb):
        msg = f"Run {run_id} not found."
        raise RunNotFoundError(msg)

    trace_rows = await database.runs.get_trace(run_id, expdb)
    if not trace_rows:
        msg = f"No trace found for run {run_id}."
        raise RunTraceNotFoundError(msg)

    return RunTrace(
        run_id=run_id,
        trace=[
            TraceIteration(
                repeat=row.repeat,
                fold=row.fold,
                iteration=row.iteration,
                setup_string=row.setup_string,
                evaluation=row.evaluation,
                selected=row.selected,
            )
            for row in trace_rows
        ],
    )
