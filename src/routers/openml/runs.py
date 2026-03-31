"""Endpoints for OpenML Run resources."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

import database.runs
from core.errors import NoResultsError, RunNotFoundError, RunTraceNotFoundError
from routers.dependencies import Pagination, expdb_connection
from routers.types import SystemString64
from schemas.runs import RunTrace, TraceIteration

router = APIRouter(prefix="/run", tags=["run"])


def _add_in_filter(
    filters: list[str],
    params: dict[str, Any],
    column: str,
    param_prefix: str,
    values: list[int],
) -> None:
    """Append an IN filter clause and its bind parameters to the query builder.

    Builds named placeholders (:prefix_0, :prefix_1, ...) for safe binding
    of multiple integer values without SQL injection risk.

    Args:
        filters: List of WHERE clause fragments to append to.
        params: Bind parameter dict to update in-place.
        column: SQL column expression (e.g. "r.rid", "a.implementation_id").
        param_prefix: Prefix for named bind params (e.g. "run_id", "flow_id").
        values: List of integer values to filter by.

    """
    placeholders = ", ".join(f":{param_prefix}_{i}" for i in range(len(values)))
    filters.append(f"{column} IN ({placeholders})")
    params |= {f"{param_prefix}_{i}": v for i, v in enumerate(values)}


@router.post(path="/list", description="Provided for convenience, same as `GET` endpoint.")
@router.get(path="/list")
async def list_runs(  # noqa: PLR0913
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
    pagination: Annotated[Pagination, Body(default_factory=Pagination)],
    run_id: Annotated[
        list[int] | None,
        Body(
            description="The run(s) to include in the search. "
            "If none are specified, all runs are included.",
        ),
    ] = None,
    task_id: Annotated[
        list[int] | None,
        Body(description="Only include runs for these task id(s)."),
    ] = None,
    flow_id: Annotated[
        list[int] | None,
        Body(description="Only include runs using these flow id(s)."),
    ] = None,
    setup_id: Annotated[
        list[int] | None,
        Body(description="Only include runs with these setup id(s)."),
    ] = None,
    uploader: Annotated[
        list[int] | None,
        Body(description="Only include runs uploaded by these user id(s)."),
    ] = None,
    tag: Annotated[
        str | None,
        SystemString64,
        Body(description="Only include runs with this tag."),
    ] = None,
) -> list[dict[str, Any]]:
    """List runs, optionally filtered by one or more criteria.

    Filters are combinable — all provided filters are applied with AND logic.
    List filters (run_id, task_id, flow_id, setup_id, uploader) accept multiple
    values and are applied with IN logic within each filter.

    Returns a flat list of run objects. Raises 404 if no runs match the filters.

    PHP equivalent: GET /run/list/[run/{ids}][/task/{ids}][/flow/{ids}]...
    Note: Unlike PHP (which requires at least one filter), this endpoint allows
    an empty filter set and returns all runs paginated.
    """
    # Clamp Pagination (Safety against massive scans or negative values)
    limit = max(1, min(pagination.limit, 1000))  # Enforce sensible limits to prevent abuse
    offset = max(0, pagination.offset)

    filters: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    # Each list filter maps a user-facing param to a SQL column.
    # flow_id maps to algorithm_setup.implementation_id (aliased as `a`).
    # setup_id maps to run.setup — the FK column stored on the run row.
    if run_id:
        _add_in_filter(filters, params, "r.rid", "run_id", run_id)
    if task_id:
        _add_in_filter(filters, params, "r.task_id", "task_id", task_id)
    if flow_id:
        _add_in_filter(filters, params, "a.implementation_id", "flow_id", flow_id)
    if setup_id:
        _add_in_filter(filters, params, "r.setup", "setup_id", setup_id)
    if uploader:
        _add_in_filter(filters, params, "r.uploader", "uploader", uploader)

    if tag is not None:
        # run_tag.id is the run FK (not a surrogate PK), so we join on run.rid
        filters.append("r.rid IN (SELECT id FROM run_tag WHERE tag = :tag)")
        params["tag"] = tag

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = text(
        f"""
        SELECT
            r.rid                       AS run_id,
            r.task_id                   AS task_id,
            r.setup                     AS setup_id,
            a.implementation_id         AS flow_id,
            r.uploader                  AS uploader,
            r.start_time                AS upload_time,
            IFNULL(r.error_message, '') AS error_message,
            IFNULL(r.run_details, '')   AS run_details
        FROM run r
        JOIN algorithm_setup a ON r.setup = a.sid
        {where_clause}
        ORDER BY r.rid
        LIMIT :limit OFFSET :offset
        """,  # noqa: S608
    )

    result = await expdb.execute(query, params)
    rows = result.mappings().all()

    if not rows:
        msg = "No runs match the search criteria."
        raise NoResultsError(msg)

    # SQLAlchemy returns start_time as a datetime object. Format to match PHP
    # response shape: "YYYY-MM-DD HH:MM:SS" (no T separator, no timezone).
    # dict unpacking with a later key overrides the earlier one from **row.
    return [
        {**row, "upload_time": row["upload_time"].strftime("%Y-%m-%d %H:%M:%S")} for row in rows
    ]


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
