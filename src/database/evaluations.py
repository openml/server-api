from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import text

from core.formatting import str_to_bool
from database.models.base import UntypedRow
from routers.schemas.tasks import EstimationProcedure

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


async def get_math_functions(
    function_type: str,
    connection: AsyncConnection,
) -> Sequence[UntypedRow]:
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
    return rows.all()


async def get_estimation_procedures(connection: AsyncConnection) -> list[EstimationProcedure]:
    row = await connection.execute(
        text(
            """
            SELECT `id`, `ttid` as 'task_type_id', `name`, `type` as 'type_',
                   `repeats`, `folds`, `stratified_sampling`, `percentage`
            FROM estimation_procedure
            """,
        ),
    )
    rows = row.mappings().all()
    typed_rows = [
        {
            k: v if k != "stratified_sampling" or v is None else str_to_bool(v)
            for k, v in row.items()
        }
        for row in rows
    ]
    return [EstimationProcedure(**typed_row) for typed_row in typed_rows]
