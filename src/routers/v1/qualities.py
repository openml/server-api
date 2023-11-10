from typing import Annotated, Literal

from database.datasets import list_all_qualities
from fastapi import APIRouter, Depends
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


@router.get("/qualities/list")
def list_qualities(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["data_qualities_list"], dict[Literal["quality"], list[str]]]:
    qualities = list_all_qualities(connection=expdb)
    return {
        "data_qualities_list": {
            "quality": qualities,
        },
    }
