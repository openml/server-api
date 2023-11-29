import http.client
from typing import Annotated, Literal

from core.access import _user_has_access
from core.errors import DatasetError
from database.datasets import get_dataset, get_qualities_for_dataset, list_all_qualities
from database.users import User
from fastapi import APIRouter, Depends, HTTPException
from schemas.datasets.openml import Quality
from sqlalchemy import Connection

from routers.dependencies import expdb_connection, fetch_user

router = APIRouter(prefix="/datasets", tags=["datasets"])


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
    user: Annotated[User, Depends(fetch_user)],
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> list[Quality]:
    dataset = get_dataset(dataset_id, expdb)
    if not dataset or not _user_has_access(dataset, user):
        raise HTTPException(
            status_code=http.client.PRECONDITION_FAILED,
            detail={"code": DatasetError.NO_DATA_FILE, "message": "Unknown dataset"},
        ) from None
    return get_qualities_for_dataset(dataset_id, expdb)
    # The PHP API provided (sometime) helpful error messages
    # if not qualities:
    # check if dataset exists: error 360
    # check if user has access: error 361
    # check if there is a data processed entry and forward the error: 364
    # if nothing in process table: 363
    # otherwise: error 362
