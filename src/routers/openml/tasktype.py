import json
from http import HTTPStatus
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy import Connection, Row

from core.errors import ProblemType, raise_problem
from database.tasks import get_input_for_task_type, get_task_types
from database.tasks import get_task_type as db_get_task_type
from routers.dependencies import expdb_connection

router = APIRouter(prefix="/tasktype", tags=["tasks"])


def _normalize_task_type(task_type: Row) -> dict[str, str | None | list[Any]]:
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


@router.get(path="/list")
def list_task_types(
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[
    Literal["task_types"],
    dict[Literal["task_type"], list[dict[str, str | None | list[Any]]]],
]:
    task_types: list[dict[str, str | None | list[Any]]] = [
        _normalize_task_type(ttype) for ttype in get_task_types(expdb)
    ]
    return {"task_types": {"task_type": task_types}}


@router.get(path="/{task_type_id}")
def get_task_type(
    task_type_id: int,
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["task_type"], dict[str, str | None | list[str] | list[dict[str, str]]]]:
    task_type_record = db_get_task_type(task_type_id, expdb)
    if task_type_record is None:
        raise_problem(
            status_code=HTTPStatus.NOT_FOUND,
            type_=ProblemType.TASK_TYPE_NOT_FOUND,
            detail="Unknown task type.",
            code=241,
        )

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
    task_type_inputs = get_input_for_task_type(task_type_id, expdb)
    input_types = []
    for task_type_input in task_type_inputs:
        input_ = {}
        if task_type_input.requirement == "required":
            input_["requirement"] = task_type_input.requirement
        input_["name"] = task_type_input.name
        # api_constraints is for one input only in the test database (TODO: patch db)
        if isinstance(task_type_input.api_constraints, str):
            constraint = json.loads(task_type_input.api_constraints)
            input_["data_type"] = constraint["data_type"]
        input_types.append(input_)
    task_type["input"] = input_types
    return {"task_type": task_type}
