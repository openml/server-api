from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

import database.datasets
import database.qualities
from core.access import _user_has_access
from core.errors import QualityError
from database.users import User
from routers.dependencies import expdb_connection, fetch_user
from schemas.datasets.openml import Quality

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/qualities/list")
def list_qualities(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["data_qualities_list"], dict[Literal["quality"], list[str]]]:
    qualities = database.qualities.list_all_qualities(connection=expdb)
    return {
        "data_qualities_list": {
            "quality": qualities,
        },
    }


@router.get("/qualities/{dataset_id}")
def get_qualities(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)],
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["data_qualities"], dict[Literal["quality"], list[Quality]]]:
    dataset = database.datasets.get(dataset_id, expdb)
    if not dataset or not _user_has_access(dataset, user):
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": QualityError.UNKNOWN_DATASET, "message": "Unknown dataset"},
        ) from None

    processing = database.datasets.get_latest_processing_update(dataset_id, expdb)
    if processing is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": QualityError.NOT_PROCESSED, "message": "Dataset not processed yet"},
        )
    if processing.error:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": QualityError.PROCESSED_WITH_ERROR, "message": "Dataset processed with error"},
        )

    qualities = database.qualities.get_for_dataset(dataset_id, expdb)
    if not qualities:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": QualityError.NO_QUALITIES, "message": "No qualities found"},
        )

    return {
        "data_qualities": {
            "quality": qualities
        }
    }
