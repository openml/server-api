from fastapi import APIRouter

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int) -> dict[str, int]:
    return {"dataset_id": dataset_id}
