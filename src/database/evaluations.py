from collections.abc import Sequence
from typing import cast

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.formatting import _str_to_bool
from schemas.datasets.openml import EstimationProcedure


async def get_math_functions(function_type: str, connection: AsyncConnection) -> Sequence[Row]:
    rows = await connection.execute(
        text(
            """
            SELECT *
            FROM math_function
            WHERE `functionType` = :function_type
            """,
        ),
        parameters={"function_type": function_type},
    )
    return cast(
        "Sequence[Row]",
        rows.all(),
    )


async def get_estimation_procedures(connection: AsyncConnection) -> list[EstimationProcedure]:
    row = await connection.execute(
        text(
            """
            SELECT `id` as 'id_', `ttid` as 'task_type_id', `name`, `type` as 'type_',
                   `repeats`, `folds`, `stratified_sampling`, `percentage`
            FROM estimation_procedure
            """,
        ),
    )
    rows = row.mappings().all()
    typed_rows = [
        {
            k: v if k != "stratified_sampling" or v is None else _str_to_bool(v)
            for k, v in row.items()
        }
        for row in rows
    ]
    return [EstimationProcedure(**typed_row) for typed_row in typed_rows]
