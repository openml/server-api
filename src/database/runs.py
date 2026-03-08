from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text


def get_run(run_id: int, expdb: Connection) -> Row | None:
    """Check if a run exists. Used to distinguish 571 (run not found) from 572 (no trace)."""
    return expdb.execute(
        text(
            """
            SELECT rid
            FROM run
            WHERE rid = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    ).one_or_none()


def get_trace(run_id: int, expdb: Connection) -> Sequence[Row]:
    """Fetch all trace iterations for a run, ordered as PHP does: repeat, fold, iteration."""
    return cast(
        "Sequence[Row]",
        expdb.execute(
            text(
                """
                SELECT `repeat`, `fold`, `iteration`, setup_string, evaluation, selected
                FROM trace
                WHERE run_id = :run_id
                ORDER BY `repeat` ASC, `fold` ASC, `iteration` ASC
                """,
            ),
            parameters={"run_id": run_id},
        ).all(),
    )
