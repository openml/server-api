from sqlalchemy import Engine, text, Connection


def get_column_names(connection: Connection, table: str) -> list[str]:
    *_, database_name = str(connection.engine.url).split("/")
    result = connection.execute(
        text(
            """
  SELECT column_name
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_NAME = :table_name AND TABLE_SCHEMA = :database
  ORDER BY ORDINAL_POSITION
  """,
        ),
        parameters={"table_name": table, "database": database_name},
    )
    return [colname for colname, in result.all()]
