from typing import Any

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
