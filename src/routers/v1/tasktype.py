import http.client
import json
from typing import Annotated, Any, Literal, cast

from database.tasks import get_input_for_task_type, get_task_types
from database.tasks import get_task_type as db_get_task_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/v1/tasktype", tags=["tasks"])


def _normalize_task_type(task_type: dict[str, str | int]) -> dict[str, str | list[Any]]:
    ttype: dict[str, str | list[Any]] = {
        k: str(v).replace("\r\n", "\n").strip() for k, v in task_type.items() if k != "id"
    }
    ttype["id"] = ttype.pop("ttid")
    if ttype["description"] == "":
        ttype["description"] = []
    return ttype


@router.get(path="/list")
def list_task_types(
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[Literal["task_types"], dict[Literal["task_type"], list[dict[str, str | list[Any]]]]]:
    task_types: list[dict[str, str | list[Any]]] = [
        _normalize_task_type(ttype) for ttype in get_task_types(expdb)
    ]
    return {"task_types": {"task_type": task_types}}


@router.get(path="/{task_type_id}")
def get_task_type(
    task_type_id: int,
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["task_type"], dict[str, str | list[str] | list[dict[str, str]]]]:
    task_type_record = db_get_task_type(task_type_id, expdb)
    if task_type_record is None:
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": "241", "message": "Unknown task type."},
        ) from None

    task_type = _normalize_task_type(task_type_record)
    task_type_inputs = get_input_for_task_type(task_type_id, expdb)
    input_types = []
    for task_type_input in task_type_inputs:
        input_ = {}
        if task_type_input["requirement"] == "required":
            input_["requirement"] = task_type_input["requirement"]
        input_["name"] = task_type_input["name"]
        constraint = json.loads(cast(str, task_type_input["api_constraints"]))
        input_["data_type"] = constraint["data_type"]
        input_types.append(input_)
    task_type["input"] = input_types
    return {"task_type": task_type}
