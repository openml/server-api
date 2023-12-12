from fastapi import APIRouter

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/{flow_id}")
def get_flow(flow_id: int) -> dict[str, int]:
    return {"flow_id": flow_id}
