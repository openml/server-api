
from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text


def enqueue(run_id: int, expdb: Connection) -> None:
    """Insert a new pending processing entry for the given run."""
    expdb.execute(
        text(
            """
            INSERT INTO processing_run(`run_id`, `status`, `date`)
            VALUES (:run_id, 'pending', :date)
            """,
        ),
        parameters={"run_id": run_id, "date": datetime.datetime.now()},
    )


def get_pending(expdb: Connection) -> Sequence[Row]:
    """Atomically claim all pending processing_run rows for this worker.

    Uses an UPDATE ... WHERE status='pending' approach so that concurrent
    workers don't double-process the same run. Claimed rows are set to
    'processing' and this worker reads them back by that status.
    """
    # Atomically mark pending rows as 'processing' so concurrent workers skip them
    expdb.execute(
        text(
            """
            UPDATE processing_run
            SET `status` = 'processing'
            WHERE `status` = 'pending'
            """,
        ),
    )
    return cast(
        "Sequence[Row]",
        expdb.execute(
            text(
                """
                SELECT `run_id`, `status`, `date`
                FROM processing_run
                WHERE `status` = 'processing'
                ORDER BY `date` ASC
                """,
            ),
        ).all(),
    )


def mark_done(run_id: int, expdb: Connection) -> None:
    """Mark a processing_run entry as successfully completed."""
    expdb.execute(
        text(
            """
            UPDATE processing_run
            SET `status` = 'done'
            WHERE `run_id` = :run_id
            """,
        ),
        parameters={"run_id": run_id},
    )


def mark_error(run_id: int, error_message: str, expdb: Connection) -> None:
    """Mark a processing_run entry as failed and store the error message."""
    expdb.execute(
        text(
            """
            UPDATE processing_run
            SET `status` = 'error', `error` = :error_message
            WHERE `run_id` = :run_id
            """,
        ),
        parameters={"run_id": run_id, "error_message": error_message},
    )
