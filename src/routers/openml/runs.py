"""Endpoints for run-related data."""

import asyncio
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
    InputDataset,
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
    # Core run record — all other data depends on uploader, setup, and task_id.
    run = await database.runs.get(run_id, expdb)
    if run is None:
        msg = f"Run {run_id} not found."
        # Reuse RunNotFoundError and pass code=236 at the call site for
        # backward compat with the PHP GET /run/{id} error code
        raise RunNotFoundError(msg, code=236)

    # Evaluation engine IDs come from config.toml [run] so they can be
    # extended when a new evaluation engine is deployed, without code changes.
    engine_ids: list[int] = config.load_run_configuration().get("evaluation_engine_ids", [1])

    # Fetch all independent data concurrently.
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
        "tuple[str | None, list[str], list[Row], list[Row], list[Row], str | None, str"
        "| None, Row | None, list[Row]]",
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

    # Flow is fetched after the gather because it requires setup.implementation_id.
    # flows.get() selects fullName AS full_name for reliable case-insensitive access.
    flow = await database.flows.get(setup.implementation_id, expdb) if setup else None

    # Build parameter_setting list from the denormalised parameter rows
    # returned by database.setups.get_parameters (which already JOINs input + implementation).
    parameter_settings = [
        ParameterSetting(
            name=p["name"],
            value=p["value"],
            component=p["flow_id"],  # implementation_id of the sub-flow owning this param
        )
        for p in parameter_rows
    ]

    input_datasets = [
        InputDataset(did=row.did, name=row.name, url=row.url) for row in input_data_rows
    ]

    # runfile.field is the file label (e.g. "description", "predictions")
    output_files = [OutputFile(file_id=row.file_id, name=row.field) for row in output_file_rows]

    evaluations = [
        EvaluationScore(
            name=row.name,
            # Whole-number floats (e.g. counts) are converted to int to match PHP's
            # integer representation. e.g. 253.0 → 253, 0.0 → 0.
            value=int(row.value)
            if isinstance(row.value, float) and row.value.is_integer()
            else row.value,
            array_data=row.array_data,
        )
        for row in evaluation_rows
    ]

    # Normalise task_evaluation_measure: empty string → None so the field is
    # excluded entirely by response_model_exclude_none=True (matches PHP behaviour
    # of returning "" but we opt to omit rather than return an empty string).
    normalised_measure = task_evaluation_measure or None

    # error_message is NULL in the DB when the run has no error.
    # The PHP response returns an empty array [] in that case.
    error_messages = [run.error_message] if run.error_message else []

    return Run(
        run_id=run_id,
        uploader=run.uploader,
        uploader_name=uploader_name,
        task_id=run.task_id,
        task_type=task_type,
        task_evaluation_measure=normalised_measure,
        flow_id=setup.implementation_id if setup else 0,
        flow_name=flow.full_name if flow else None,
        setup_id=run.setup,
        setup_string=setup.setup_string if setup else None,
        parameter_setting=parameter_settings,
        error_message=error_messages,
        tag=tags,
        # Preserve PHP envelope structure for backward compat
        input_data={"dataset": input_datasets},
        output_data={"file": output_files, "evaluation": evaluations},
    )
