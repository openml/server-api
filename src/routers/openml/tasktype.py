import json
import logging
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import TaskTypeNotFoundError
from database.tasks import get_input_for_task_type, get_task_types
from database.tasks import get_task_type as db_get_task_type
from routers.dependencies import expdb_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasktype", tags=["tasks"])


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


def parse_api_constraints(
    api_constraints: Any,
    *,
    task_type_id: int,
    input_name: str,
) -> str | None:
    """Defensively parse api_constraints and extract a valid data_type string.

    Malformed api_constraints will not raise errors; instead they are logged
    and ignored for response construction. Returns a non-empty data_type string
    on success, or None if the value cannot be parsed or does not contain a
    valid data_type.
    """
    constraint: dict[str, Any] | None = None

    if api_constraints is None:
        return None

    if isinstance(api_constraints, dict):
        constraint = api_constraints
    elif isinstance(api_constraints, str):
        if not api_constraints:
            logger.warning(
                "api_constraints: empty_string for task_type_id=%d, input=%s",
                task_type_id,
                input_name,
            )
            return None
        try:
            parsed = json.loads(api_constraints)
        except json.JSONDecodeError:
            logger.warning(
                "api_constraints: malformed_json for task_type_id=%d, input=%s",
                task_type_id,
                input_name,
            )
            return None
        if not isinstance(parsed, dict):
            logger.warning(
                "api_constraints: non_dict_json for task_type_id=%d, input=%s (got %s)",
                task_type_id,
                input_name,
                type(parsed).__name__,
            )
            return None
        constraint = parsed
    else:
        logger.warning(
            "api_constraints: unsupported_type for task_type_id=%d, input=%s (got %s)",
            task_type_id,
            input_name,
            type(api_constraints).__name__,
        )
        return None

    data_type = constraint.get("data_type")
    if not isinstance(data_type, str) or not data_type:
        logger.debug(
            "api_constraints: missing_data_type for task_type_id=%d, input=%s",
            task_type_id,
            input_name,
        )
        return None

    return data_type


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
    """Retrieve a task type by ID.

    Response contract:
    - Always returns 200 for valid task types.
    - input[].data_type is optional and only included when valid constraints exist.
    - Invalid api_constraints never break the response.
    """
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
        # data_type is optional and only included when valid constraints exist.
        # Malformed api_constraints will not raise errors; instead they are
        # logged and ignored for response construction.
        data_type = parse_api_constraints(
            task_type_input.api_constraints,
            task_type_id=task_type_id,
            input_name=task_type_input.name,
        )
        if data_type is not None:
            input_["data_type"] = data_type
        input_types.append(input_)
    task_type["input"] = input_types
    return {"task_type": task_type}
