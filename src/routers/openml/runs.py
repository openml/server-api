from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.runs
from core.tagging import tag_entity, untag_entity
from database.users import User
from routers.dependencies import expdb_connection, fetch_user_or_raise
from routers.types import SystemString64

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post(path="/tag")
async def tag_run(
    run_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, Any]]:
    return await tag_entity(
        run_id,
        tag,
        user,
        expdb,
        get_tags_fn=database.runs.get_tags,
        tag_fn=database.runs.tag,
        response_key="run_tag",
    )


@router.post(path="/untag")
async def untag_run(
    run_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User, Depends(fetch_user_or_raise)],
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[str, dict[str, Any]]:
    return await untag_entity(
        run_id,
        tag,
        user,
        expdb,
        get_tag_fn=database.runs.get_tag,
        delete_tag_fn=database.runs.delete_tag,
        get_tags_fn=database.runs.get_tags,
        response_key="run_tag",
    )
