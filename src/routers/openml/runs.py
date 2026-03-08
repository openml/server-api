from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

import database.runs
from routers.dependencies import expdb_connection
from schemas.runs import RunTrace, RunTraceResponse, TraceIteration

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/trace/{run_id}")
def get_run_trace(
    run_id: int,
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> RunTraceResponse:
    # 571: run does not exist at all
    if not database.runs.get_run(run_id, expdb):
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "571", "message": "Run not found."},
        )

    trace_rows = database.runs.get_trace(run_id, expdb)

    # 572: run exists but has no trace data
    if not trace_rows:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "572", "message": "No trace found for run."},
        )

    return RunTraceResponse(
        trace=RunTrace(
            # Cast to str: PHP returns run_id and all iteration fields as strings.
            run_id=str(run_id),
            trace_iteration=[
                TraceIteration(
                    repeat=str(row.repeat),
                    fold=str(row.fold),
                    iteration=str(row.iteration),
                    setup_string=row.setup_string,
                    evaluation=row.evaluation,
                    selected=row.selected,
                )
                for row in trace_rows
            ],
        ),
    )
