"""Endpoints for run-related data."""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, cast

from fastapi import APIRouter, Depends

import config
import database.flows
import database.runs
import database.setups
import database.tasks
import database.users
from core.errors import RunNotFoundError, RunTraceNotFoundError
from database.schema.base import UntypedRow
from routers.dependencies import expdb_connection, userdb_connection
from routers.types import Identifier
from schemas.runs import (
    EvaluationScore,
    InputDataset,
    OutputData,
    OutputFile,
    ParameterSetting,
    Run,
    RunTrace,
    TraceIteration,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

router = APIRouter(prefix="/run", tags=["run"])


@router.get("/trace/{run_id}")
async def get_run_trace(
    run_id: Identifier,
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


@dataclass
class RunContext:
    """Helper context to store concurrently fetched run dependencies."""

    uploader_name: str | None
    tags: list[str]
    input_data_rows: list[UntypedRow]
    output_file_rows: list[UntypedRow]
    evaluation_rows: list[UntypedRow]
    task_type: str | None
    task_evaluation_measure: str | None
    setup: UntypedRow | None
    parameter_rows: list[UntypedRow]


async def _load_run_context(
    run: UntypedRow,
    run_id: int,
    expdb: AsyncConnection,
    userdb: AsyncConnection,
    engine_ids: list[int],
) -> RunContext:
    (
        uploader_user,
        tags,
        input_data_rows,
        output_file_rows,
        evaluation_rows,
        task_type,
        task_evaluation_measure,
        setup,
        parameter_rows,
    ) = cast(
        "tuple[Any, list[str], list[UntypedRow], list[UntypedRow], list[UntypedRow], str | None, str | None, UntypedRow | None, list[UntypedRow]]",  # noqa: E501
        await asyncio.gather(
            database.users.get_user(user_id=run.uploader, connection=userdb),
            database.runs.get_tags(run_id, expdb),
            database.runs.get_input_data(run_id, expdb),
            database.runs.get_output_files(run_id, expdb),
            database.runs.get_evaluations(run_id, expdb, evaluation_engine_ids=engine_ids),
            database.tasks.get_task_type_name(run.task_id, expdb),
            database.tasks.get_task_evaluation_measure(run.task_id, expdb),
            database.setups.get(run.setup, expdb),
            database.setups.get_parameters(run.setup, expdb),
        ),
    )
    return RunContext(
        uploader_name=uploader_user.full_name if uploader_user else None,
        tags=tags,
        input_data_rows=input_data_rows,
        output_file_rows=output_file_rows,
        evaluation_rows=evaluation_rows,
        task_type=task_type,
        task_evaluation_measure=task_evaluation_measure,
        setup=setup,
        parameter_rows=parameter_rows,
    )


def _build_evaluations(rows: list[UntypedRow]) -> list[EvaluationScore]:
    def _normalise_value(v: object) -> object:
        if isinstance(v, (int, float)):
            return int(v) if float(v).is_integer() else float(v)
        return v

    return [
        EvaluationScore(
            name=row.name,
            value=_normalise_value(row.value),
            array_data=row.array_data,
            repeat=getattr(row, "repeat", None),
            fold=getattr(row, "fold", None),
        )
        for row in rows
    ]


@router.get("/{run_id}", response_model_exclude_none=True)
async def get_run(
    run_id: int,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
    userdb: Annotated[AsyncConnection, Depends(userdb_connection)],
) -> Run:
    """Get full metadata for a run by ID.

    No authentication or visibility check is performed — all runs are
    publicly accessible.
    """
    run = await database.runs.get(run_id, expdb)
    if run is None:
        msg = f"Run {run_id} not found."
        raise RunNotFoundError(msg, code=236)

    engine_ids: list[int] = config.get_config().development.run_evaluation_engine_ids
    ctx = await _load_run_context(run, run_id, expdb, userdb, engine_ids)

    flow = await database.flows.get(ctx.setup.implementation_id, expdb) if ctx.setup else None
    evaluations = _build_evaluations(ctx.evaluation_rows)

    normalised_measure = ctx.task_evaluation_measure or None
    error_messages = [run.error_message] if run.error_message else []

    return Run(
        run_id=run_id,
        uploader=run.uploader,
        uploader_name=ctx.uploader_name,
        task_id=run.task_id,
        task_type=ctx.task_type,
        task_evaluation_measure=normalised_measure,
        flow_id=ctx.setup.implementation_id if ctx.setup else None,
        flow_name=flow.full_name if flow else None,
        setup_id=run.setup,
        setup_string=ctx.setup.setup_string if ctx.setup else None,
        parameter_setting=[
            ParameterSetting(name=p.name, value=p.value, component=p.flow_id)
            for p in ctx.parameter_rows
        ],
        error_message=error_messages,
        tag=ctx.tags,
        input_data=[InputDataset(did=r.did, name=r.name, url=r.url) for r in ctx.input_data_rows],
        output_data=OutputData(
            file=[OutputFile(file_id=r.file_id, name=r.field) for r in ctx.output_file_rows],
            evaluation=evaluations,
        ),
    )
