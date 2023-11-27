from typing import Annotated, Literal

from database.datasets import list_all_qualities
from fastapi import APIRouter, Depends
from schemas.datasets.openml import Quality
from sqlalchemy import Connection, text

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


@router.get("/qualities/{dataset_id}")
def get_qualities(
    dataset_id: int,
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> list[Quality]:
    rows = expdb.execute(
        text(
            """
        SELECT `quality`,`value`
        FROM data_quality
        WHERE `data`=:dataset_id
        """,
        ),
        parameters={"dataset_id": dataset_id},
    )
    return [Quality(name=row.quality, value=row.value) for row in rows]
