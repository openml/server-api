from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/studies", tags=["studies"])


@router.get("/{study_id}")
def get_study(study_id: int) -> dict[str, Any]:
    return {"id": study_id, "name": "test study"}
