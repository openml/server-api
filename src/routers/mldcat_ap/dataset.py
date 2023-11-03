from typing import Annotated

from database.setup import expdb_database, user_database
from fastapi import APIRouter, Depends
from schemas.datasets.mldcat_ap import JsonLDGraph, convert_to_mldcat_ap
from sqlalchemy import Engine

from routers.datasets import get_dataset

router = APIRouter(prefix="/mldcat_ap/datasets", tags=["datasets"])


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_mldcat_ap_dataset(
    dataset_id: int,
    user_db: Annotated[Engine, Depends(user_database)],
    expdb_db: Annotated[Engine, Depends(expdb_database)],
) -> JsonLDGraph:
    openml_dataset = get_dataset(
        dataset_id=dataset_id,
        user_db=user_db,
        expdb_db=expdb_db,
    )
    return convert_to_mldcat_ap(openml_dataset)
