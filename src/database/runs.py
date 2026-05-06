"""Database queries for run-related data."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from sqlalchemy import Row, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


async def exist(id_: int, expdb: AsyncConnection) -> bool:
    """Check if a run exists by ID."""
    row = await expdb.execute(
        text(
            """
            SELECT 1
            FROM `run`
            WHERE `rid` = :run_id
            """,
        ),
        parameters={"run_id": id_},
    )
    return bool(row.one_or_none())


async def get_trace(run_id: int, expdb: AsyncConnection) -> Sequence[Row]:
    """Get trace rows for a run from the trace table."""
    rows = await expdb.execute(
        text(
            """
            SELECT `repeat`, `fold`, `iteration`, `setup_string`, `evaluation`, `selected`
            FROM `trace`
            WHERE `run_id` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )
