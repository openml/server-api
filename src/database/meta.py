from sqlalchemy import Engine, text


def get_column_names(database_engine: Engine, table: str) -> list[str]:
    *_, database_name = str(database_engine.url).split("/")
    with database_engine.connect() as conn:
        result = conn.execute(
            text(
                """
      SELECT column_name
      FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_NAME = :table_name AND TABLE_SCHEMA = :database;
      """,
            ),
            parameters={"table_name": table, "database": database_name},
        )
    return [colname for colname, in result.all()]
