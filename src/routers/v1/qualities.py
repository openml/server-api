import http.client
from typing import Annotated, Any, Literal

from database.datasets import get_dataset, list_all_qualities
from database.users import User, UserGroup
from fastapi import APIRouter, Depends, HTTPException
from schemas.datasets.openml import Quality
from sqlalchemy import Connection, text

from routers.dependencies import expdb_connection, fetch_user
from routers.v2.datasets import DatasetError

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


def _user_can_see_dataset(dataset: dict[str, Any], user: User) -> bool:
    if dataset["visibility"] == "public":
        return True
    return user is not None and (
        dataset["uploader"] == user.user_id or UserGroup.ADMIN in user.groups
    )


@router.get("/qualities/{dataset_id}")
def get_qualities(
    dataset_id: int,
    user: Annotated[User, Depends(fetch_user)],
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> list[Quality]:
    dataset = get_dataset(dataset_id, expdb)
    if not dataset or not _user_can_see_dataset(dataset, user):
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": DatasetError.NO_DATA_FILE, "message": "Unknown dataset"},
        ) from None
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
    # The PHP API provided (sometime) helpful error messages
    # if not qualities:
    # check if dataset exists: error 360
    # check if user has access: error 361
    # check if there is a data processed entry and forward the error: 364
    # if nothing in process table: 363
    # otherwise: error 362
