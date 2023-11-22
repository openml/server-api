from typing import Annotated, Literal

from database.tasks import get_task_types
from fastapi import APIRouter, Depends
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/v1/tasktype", tags=["tasks"])


@router.get(path="/list")
def list_task_types(
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[Literal["task_types"], dict[Literal["task_type"], list[dict[str, str]]]]:
    task_types = [{k: str(v) for k, v in ttype.items()} for ttype in get_task_types(expdb)]
    return {"task_types": {"task_type": task_types}}
