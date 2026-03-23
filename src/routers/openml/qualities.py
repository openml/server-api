from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.datasets
import database.qualities
from core.access import _user_has_access
from core.errors import (
    DatasetNotFoundError,
    QualityDatasetNotProcessedError,
    QualityDatasetProcessingError,
    QualityNoQualitiesError,
)
from database.users import User
from routers.dependencies import expdb_connection, fetch_user
from schemas.datasets.openml import Quality

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/qualities/list")
async def list_qualities(
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> dict[Literal["data_qualities_list"], dict[Literal["quality"], list[str]]]:
    qualities = await database.qualities.list_all_qualities(connection=expdb)
    return {
        "data_qualities_list": {
            "quality": qualities,
        },
    }


@router.get("/qualities/{dataset_id}")
async def get_qualities(
    dataset_id: int,
    user: Annotated[User | None, Depends(fetch_user)],
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> list[Quality]:
    dataset = await database.datasets.get(dataset_id, expdb)
    if not dataset or not await _user_has_access(dataset, user):
        # Backwards compatibility: PHP API returns 412 with code 113
        msg = f"Dataset with id {dataset_id} not found."
        raise DatasetNotFoundError(
            msg,
            code=361,
        ) from None

    processing = await database.datasets.get_latest_processing_update(dataset_id, expdb)
    if processing is None:
        msg = f"Dataset not processed yet for dataset {dataset_id}."
        raise QualityDatasetNotProcessedError(msg)

    if processing.error:
        raise QualityDatasetProcessingError(processing.error.strip())

    qualities = await database.qualities.get_for_dataset(dataset_id, expdb)
    if not qualities:
        msg = f"No qualities found for dataset {dataset_id}."
        raise QualityNoQualitiesError(msg)

    return qualities
