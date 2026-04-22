"""Endpoints for run-related data."""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncConnection

import config
import database.flows
import database.runs
import database.setups
from core.errors import RunNotFoundError, RunTraceNotFoundError
from routers.dependencies import expdb_connection, userdb_connection
from schemas.runs import (
    EvaluationScore,
    InputData,
    InputDataset,
    OutputData,
    OutputFile,
    ParameterSetting,
    Run,
    RunTrace,
    TraceIteration,
)

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


@dataclass
class RunContext:
    """Helper context to store concurrently fetched run dependencies."""

    uploader_name: str | None
    tags: list[str]
    input_data_rows: list["Row"]
    output_file_rows: list["Row"]
    evaluation_rows: list["Row"]
    task_type: str | None
    task_evaluation_measure: str | None
    setup: "Row | None"
    parameter_rows: list["Row"]


async def _load_run_context(
    run: "Row",
    run_id: int,
    expdb: AsyncConnection,
    userdb: AsyncConnection,
    engine_ids: list[int],
) -> RunContext:
    (
        uploader_name,
        tags,
        input_data_rows,
        output_file_rows,
        evaluation_rows,
        task_type,
        task_evaluation_measure,
        setup,
        parameter_rows,
    ) = cast(
        "tuple[str | None, list[str], list[Row], list[Row], list[Row], str | None, str |"
        "None, Row | None, list[Row]]",
        await asyncio.gather(
            database.runs.get_uploader_name(run.uploader, userdb),
            database.runs.get_tags(run_id, expdb),
            database.runs.get_input_data(run_id, expdb),
            database.runs.get_output_files(run_id, expdb),
            database.runs.get_evaluations(run_id, expdb, evaluation_engine_ids=engine_ids),
            database.runs.get_task_type(run.task_id, expdb),
            database.runs.get_task_evaluation_measure(run.task_id, expdb),
            database.setups.get(run.setup, expdb),
            database.setups.get_parameters(run.setup, expdb),
        ),
    )
    return RunContext(
        uploader_name=uploader_name,
        tags=tags,
        input_data_rows=input_data_rows,
        output_file_rows=output_file_rows,
        evaluation_rows=evaluation_rows,
        task_type=task_type,
        task_evaluation_measure=task_evaluation_measure,
        setup=setup,
        parameter_rows=parameter_rows,
    )


def _build_parameter_settings(parameter_rows: list["Row"]) -> list[ParameterSetting]:
    return [
        ParameterSetting(
            name=p["name"],
            value=p["value"],
            component=p["flow_id"],
        )
        for p in parameter_rows
    ]


def _build_input_datasets(rows: list["Row"]) -> list[InputDataset]:
    return [InputDataset(did=row.did, name=row.name, url=row.url) for row in rows]


def _build_output_files(rows: list["Row"]) -> list[OutputFile]:
    return [OutputFile(file_id=row.file_id, name=row.field) for row in rows]


def _build_evaluations(rows: list["Row"]) -> list[EvaluationScore]:
    def _normalise_value(v: object) -> object:
        if isinstance(v, (int, float)):
            return int(v) if float(v).is_integer() else v
        if isinstance(v, str):
            try:
                f = float(v)
                return int(f) if f.is_integer() else f
            except ValueError:
                return None
        return None

    return [
        EvaluationScore(
            name=row.name,
            value=_normalise_value(row.value),
            array_data=row.array_data,
        )
        for row in rows
    ]


@router.post(
    path="/{run_id}",
    description="Provided for convenience, same as `GET` endpoint.",
    response_model_exclude_none=True,
)
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

    engine_ids: list[int] = config.load_run_configuration().get("evaluation_engine_ids", [1])
    ctx = await _load_run_context(run, run_id, expdb, userdb, engine_ids)

    flow = await database.flows.get(ctx.setup.implementation_id, expdb) if ctx.setup else None

    parameter_settings = _build_parameter_settings(ctx.parameter_rows)
    input_datasets = _build_input_datasets(ctx.input_data_rows)
    output_files = _build_output_files(ctx.output_file_rows)
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
        parameter_setting=parameter_settings,
        error_message=error_messages,
        tag=ctx.tags,
        input_data=InputData(dataset=input_datasets),
        output_data=OutputData(file=output_files, evaluation=evaluations),
    )
