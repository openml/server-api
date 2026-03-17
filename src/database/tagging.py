from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncConnection


async def insert_tag(
    *,
    table: str,
    id_column: str,
    id_: int,
    tag_: str,
    user_id: int,
    expdb: AsyncConnection,
) -> None:
    await expdb.execute(
        text(
            f"""
            INSERT INTO {table}(`{id_column}`, `tag`, `uploader`)
            VALUES (:id, :tag, :user_id)
            """,
        ),
        parameters={"id": id_, "tag": tag_, "user_id": user_id},
    )


async def select_tag(
    *,
    table: str,
    id_column: str,
    id_: int,
    tag_: str,
    expdb: AsyncConnection,
) -> Row | None:
    result = await expdb.execute(
        text(
            f"""
            SELECT `{id_column}` as id, `tag`, `uploader`
            FROM {table}
            WHERE `{id_column}` = :id AND `tag` = :tag
            """,
        ),
        parameters={"id": id_, "tag": tag_},
    )
    return result.one_or_none()


async def remove_tag(
    *,
    table: str,
    id_column: str,
    id_: int,
    tag_: str,
    expdb: AsyncConnection,
) -> None:
    await expdb.execute(
        text(
            f"""
            DELETE FROM {table}
            WHERE `{id_column}` = :id AND `tag` = :tag
            """,
        ),
        parameters={"id": id_, "tag": tag_},
    )


async def select_tags(
    *,
    table: str,
    id_column: str,
    id_: int,
    expdb: AsyncConnection,
) -> list[str]:
    result = await expdb.execute(
        text(
            f"""
            SELECT `tag`
            FROM {table}
            WHERE `{id_column}` = :id
            """,
        ),
        parameters={"id": id_},
    )
    return [row.tag for row in result.all()]
