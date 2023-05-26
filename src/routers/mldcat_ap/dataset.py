from fastapi import APIRouter
from schemas.datasets.mldcat_ap import JsonLDGraph, convert_to_mldcat_ap

from routers.datasets import get_dataset

router = APIRouter(prefix="/mldcat_ap/datasets", tags=["datasets"])


@router.get(
    path="/{dataset_id}",
    description="Get meta-data for dataset with ID `dataset_id`.",
)
def get_mldcat_ap_dataset(dataset_id: int) -> JsonLDGraph:
    openml_dataset = get_dataset(dataset_id)
    return convert_to_mldcat_ap(openml_dataset)
