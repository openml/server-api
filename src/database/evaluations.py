"""Database functions for retrieving evaluation-related data."""

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Connection, Row, text

from core.formatting import _str_to_bool
from schemas.datasets.openml import EstimationProcedure


def get_math_functions(function_type: str, connection: Connection) -> Sequence[Row]:
    """Get math functions by type."""
    return cast(
        "Sequence[Row]",
        connection.execute(
            text(
                """
            SELECT *
            FROM math_function
            WHERE `functionType` = :function_type
            """,
            ),
            parameters={"function_type": function_type},
        ).all(),
    )


def get_estimation_procedures(connection: Connection) -> list[EstimationProcedure]:
    """Get all estimation procedures."""
    rows = connection.execute(
        text(
            """
            SELECT `id` as 'id_', `ttid` as 'task_type_id', `name`, `type` as 'type_',
                   `repeats`, `folds`, `stratified_sampling`, `percentage`
            FROM estimation_procedure
            """,
        ),
    )
    typed_rows = [
        {
            k: v if k != "stratified_sampling" or v is None else _str_to_bool(v)
            for k, v in row.items()
        }
        for row in rows.mappings()
    ]
    return [EstimationProcedure(**typed_row) for typed_row in typed_rows]
