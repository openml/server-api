from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

import database.evaluations
from routers.dependencies import expdb_connection
from schemas.datasets.openml import EstimationProcedure

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
async def get_estimation_procedures(
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> list[EstimationProcedure]:
    procedures = await database.evaluations.get_estimation_procedures(expdb)
    return list(procedures)
