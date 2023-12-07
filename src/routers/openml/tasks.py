from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(
    # task_id: int,
    # user: Annotated[User | None, Depends(fetch_user)] = None,
    # expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, Any]:
    return {}
