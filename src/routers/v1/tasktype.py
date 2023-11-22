from typing import Annotated, Any, Literal

from database.tasks import get_task_types
from fastapi import APIRouter, Depends
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/v1/tasktype", tags=["tasks"])


@router.get(path="/list")
def list_task_types(
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[Literal["task_types"], dict[Literal["task_type"], list[dict[str, str | list[Any]]]]]:
    task_types: list[dict[str, str | list[Any]]] = [
        {k: str(v).replace("\r\n", "\n").strip() for k, v in ttype.items() if k != "id"}
        for ttype in get_task_types(expdb)
    ]
    for task_type in task_types:
        task_type["id"] = task_type.pop("ttid")
        if task_type["description"] == "":
            task_type["description"] = []
    return {"task_types": {"task_type": task_types}}
