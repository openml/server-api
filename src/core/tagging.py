from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import TagAlreadyExistsError, TagNotFoundError, TagNotOwnedError
from database.users import User, UserGroup


async def tag_entity(
    entity_id: int,
    tag: str,
    user: User,
    expdb: AsyncConnection,
    *,
    get_tags_fn: Callable[[int, AsyncConnection], Awaitable[list[str]]],
    tag_fn: Callable[..., Awaitable[None]],
    response_key: str,
) -> dict[str, dict[str, Any]]:
    tags = await get_tags_fn(entity_id, expdb)
    if tag.casefold() in (t.casefold() for t in tags):
        msg = f"Entity {entity_id} already tagged with {tag!r}."
        raise TagAlreadyExistsError(msg)
    await tag_fn(entity_id, tag, user_id=user.user_id, expdb=expdb)
    tags = await get_tags_fn(entity_id, expdb)
    return {response_key: {"id": str(entity_id), "tag": tags}}


async def untag_entity(
    entity_id: int,
    tag: str,
    user: User,
    expdb: AsyncConnection,
    *,
    get_tag_fn: Callable[[int, str, AsyncConnection], Awaitable[Row | None]],
    delete_tag_fn: Callable[[int, str, AsyncConnection], Awaitable[None]],
    get_tags_fn: Callable[[int, AsyncConnection], Awaitable[list[str]]],
    response_key: str,
) -> dict[str, dict[str, Any]]:
    existing = await get_tag_fn(entity_id, tag, expdb)
    if existing is None:
        msg = f"Tag {tag!r} not found on entity {entity_id}."
        raise TagNotFoundError(msg)
    groups = await user.get_groups()
    if existing.uploader != user.user_id and UserGroup.ADMIN not in groups:
        msg = f"Tag {tag!r} on entity {entity_id} is not owned by you."
        raise TagNotOwnedError(msg)
    await delete_tag_fn(entity_id, tag, expdb)
    tags = await get_tags_fn(entity_id, expdb)
    return {response_key: {"id": str(entity_id), "tag": tags}}
