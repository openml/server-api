"""All database operations that directly operate on setups."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from core.types import Identifier, TagString
from database.exceptions import (
    _DUPLICATE_ENTRY,
    _FOREIGN_KEY_CONSTRAINT_FAILED,
    DuplicatePrimaryKeyError,
    ForeignKeyConstraintError,
)
from database.models.setups import Setup
from database.models.tags import SetupTag

if TYPE_CHECKING:
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession


async def get(setup_id: Identifier, session: AsyncSession) -> Setup | None:
    """Get the setup with id `setup_id` from the database."""
    return await session.get(Setup, setup_id)


async def get_parameters(setup_id: Identifier, connection: AsyncConnection) -> list[RowMapping]:
    """Get all parameters for setup with `setup_id` from the database."""
    rows = await connection.execute(
        text(
            """
            SELECT
                t_input.id as id,
                t_input.implementation_id as flow_id,
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


async def get_tags(setup_id: Identifier, session: AsyncSession) -> Sequence[SetupTag]:
    """Get all tags for setup with `setup_id` from the database."""
    stmt = select(SetupTag).where(SetupTag.entity_id == setup_id)
    return (await session.scalars(stmt)).all()


async def get_tag(setup_id: Identifier, tag: TagString, session: AsyncSession) -> SetupTag | None:
    """Get the tag `tag` for setup with id `setup_id`."""
    return await session.get(SetupTag, {"tag": tag, "entity_id": setup_id})


async def delete_tag(tag: SetupTag, session: AsyncSession) -> None:
    """Delete a setup tag."""
    await session.delete(tag)


async def tag(
    setup_id: Identifier,
    tag: TagString,
    user_id: Identifier,
    session: AsyncSession,
) -> None:
    """Add tag `tag` to setup with id `setup_id`."""
    tag_ = SetupTag(entity_id=setup_id, tag=tag, uploader_id=user_id)
    try:
        session.add(tag_)
        await session.flush()
    except IntegrityError as e:
        if e.orig is None:
            raise
        code, msg = e.orig.args
        if code == _FOREIGN_KEY_CONSTRAINT_FAILED:
            raise ForeignKeyConstraintError(msg) from e
        if code == _DUPLICATE_ENTRY:
            raise DuplicatePrimaryKeyError(msg) from e
        raise
