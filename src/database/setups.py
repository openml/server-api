"""All database operations that directly operate on setups."""

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection


async def get(setup_id: int, connection: AsyncConnection) -> Row | None:
    """Get the setup with id `setup_id` from the database."""
    row = await connection.execute(
        text(
            """
            SELECT *
            FROM algorithm_setup
            WHERE sid = :setup_id
            """,
        ),
        parameters={"setup_id": setup_id},
    )
    return row.first()


async def get_tags(setup_id: int, connection: AsyncConnection) -> list[Row]:
    """Get all tags for setup with `setup_id` from the database."""
    rows = await connection.execute(
        text(
            """
            SELECT *
            FROM setup_tag
            WHERE id = :setup_id
            """,
        ),
        parameters={"setup_id": setup_id},
    )
    return list(rows.all())


async def untag(setup_id: int, tag: str, connection: AsyncConnection) -> None:
    """Remove tag `tag` from setup with id `setup_id`."""
    await connection.execute(
        text(
            """
            DELETE FROM setup_tag
            WHERE id = :setup_id AND tag = :tag
            """,
        ),
        parameters={"setup_id": setup_id, "tag": tag},
    )
