from typing import Annotated

from fastapi import APIRouter, Depends
from schemas.datasets.mldcat_ap import JsonLDGraph, convert_to_mldcat_ap
from sqlalchemy import Connection

from routers.dependencies import expdb_connection, userdb_connection
from routers.openml.datasets import get_dataset

router = APIRouter(prefix="/mldcat_ap/datasets", tags=["MLDCAT-AP"])


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_mldcat_ap_dataset(
    dataset_id: int,
    user_db: Annotated[Connection, Depends(userdb_connection)] = None,
    expdb_db: Annotated[Connection, Depends(expdb_connection)] = None,
) -> JsonLDGraph:
    openml_dataset = get_dataset(
        dataset_id=dataset_id,
        user_db=user_db,
        expdb_db=expdb_db,
    )
    return convert_to_mldcat_ap(openml_dataset)
