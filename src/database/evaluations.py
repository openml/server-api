from typing import Any, Iterable

from core.formatting import _str_to_bool
from schemas.datasets.openml import EstimationProcedure
from sqlalchemy import Connection, CursorResult, text


def get_math_functions(function_type: str, connection: Connection) -> CursorResult[Any]:
    return connection.execute(
        text(
            """
            SELECT *
            FROM math_function
            WHERE `functionType` = :function_type
            """,
        ),
        parameters={"function_type": function_type},
    )


def get_estimation_procedures(connection: Connection) -> Iterable[EstimationProcedure]:
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
