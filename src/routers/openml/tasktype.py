import json
import logging
from collections.abc import Mapping
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import TaskTypeNotFoundError
from database.tasks import get_input_for_task_type, get_task_types
from database.tasks import get_task_type as db_get_task_type
from routers.dependencies import expdb_connection

router = APIRouter(prefix="/tasktype", tags=["tasks"])
logger = logging.getLogger(__name__)


def _normalize_task_type(task_type: Row[Any]) -> dict[str, str | None | list[Any]]:
    # Task types may contain multi-line fields which have either \r\n or \n line endings
    ttype: dict[str, str | None | list[Any]] = {
        k: str(v).replace("\r\n", "\n").strip() if v is not None else v
        for k, v in task_type._mapping.items()  # noqa: SLF001
        if k != "id"
    }
    ttype["id"] = ttype.pop("ttid")
    if ttype["description"] == "":
        ttype["description"] = []
    return ttype


def _extract_data_type_from_api_constraints(
    api_constraints: Mapping[str, Any] | str | None,
    input_name: str,
) -> str | None:
    """Extract string data_type from api_constraints safely."""
    constraint: Mapping[str, Any] | None = None

    if isinstance(api_constraints, str):
        try:
            loaded = json.loads(api_constraints)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to decode legacy api_constraints JSON for task_type_input '%s'; value=%r",
                input_name,
                api_constraints,
                exc_info=True,
            )
            return None
        if isinstance(loaded, Mapping):
            constraint = loaded
    elif isinstance(api_constraints, Mapping):
        constraint = api_constraints

    if not constraint:
        return None

    data_type = constraint.get("data_type")
    return data_type if isinstance(data_type, str) else None


@router.get(path="/list")
async def list_task_types(
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[
    Literal["task_types"],
    dict[Literal["task_type"], list[dict[str, str | None | list[Any]]]],
]:
    task_types: list[dict[str, str | None | list[Any]]] = [
        _normalize_task_type(ttype) for ttype in await get_task_types(expdb)
    ]
    return {"task_types": {"task_type": task_types}}


@router.get(path="/{task_type_id}")
async def get_task_type(
    task_type_id: int,
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[Literal["task_type"], dict[str, str | None | list[str] | list[dict[str, str]]]]:
    task_type_record = await db_get_task_type(task_type_id, expdb)
    if task_type_record is None:
        msg = f"Task type {task_type_id} not found."
        raise TaskTypeNotFoundError(msg)

    task_type = _normalize_task_type(task_type_record)
    # Some names are quoted, or have typos in their comma-separation (e.g. 'A ,B')
    task_type["creator"] = [
        creator.strip(' "') for creator in cast("str", task_type["creator"]).split(",")
    ]
    if contributors := task_type.pop("contributors"):
        task_type["contributor"] = [
            creator.strip(' "') for creator in cast("str", contributors).split(",")
        ]
    task_type["creation_date"] = task_type.pop("creationDate")

    task_type_inputs = await get_input_for_task_type(task_type_id, expdb)
    input_types = []
    for task_type_input in task_type_inputs:
        input_ = {}
        if task_type_input.requirement == "required":
            input_["requirement"] = task_type_input.requirement
        input_["name"] = task_type_input.name

        data_type = _extract_data_type_from_api_constraints(
            task_type_input.api_constraints,
            task_type_input.name,
        )
        if data_type is not None:
            input_["data_type"] = data_type

        input_types.append(input_)

    task_type["input"] = input_types
    return {"task_type": task_type}
