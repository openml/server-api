"""All database operations that directly operate on setups."""

from sqlalchemy import text
from sqlalchemy.engine import Row, RowMapping
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


async def get_parameters(setup_id: int, connection: AsyncConnection) -> list[RowMapping]:
    """Get all parameters for setup with `setup_id` from the database."""
    rows = await connection.execute(
        text(
            """
            SELECT
                CAST(t_input.id AS CHAR) as id,
                CAST(t_input.implementation_id AS CHAR) as flow_id,
                t_impl.name AS flow_name,
                CONCAT(t_impl.fullName, '_', t_input.name) AS full_name,
                t_input.name AS parameter_name,
                t_input.name AS name,
                t_input.dataType AS data_type,
                t_input.defaultValue AS default_value,
                t_setting.value AS value
            FROM input_setting t_setting
            JOIN input t_input ON t_setting.input_id = t_input.id
            JOIN implementation t_impl ON t_input.implementation_id = t_impl.id
            WHERE t_setting.setup = :setup_id
            ORDER BY t_impl.id, t_input.id
            """,
        ),
        parameters={"setup_id": setup_id},
    )
    return list(rows.mappings().all())


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


async def tag(setup_id: int, tag: str, user_id: int, connection: AsyncConnection) -> None:
    """Add tag `tag` to setup with id `setup_id`."""
    await connection.execute(
        text(
            """
            INSERT INTO setup_tag (id, tag, uploader)
            VALUES (:setup_id, :tag, :user_id)
            """,
        ),
        parameters={"setup_id": setup_id, "tag": tag, "user_id": user_id},
    )
