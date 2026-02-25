from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.evaluations
from routers.dependencies import expdb_connection
from schemas.datasets.openml import EstimationProcedure

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
async def get_estimation_procedures(
    expdb: Annotated[AsyncConnection, Depends(expdb_connection)],
) -> Iterable[EstimationProcedure]:
    return await database.evaluations.get_estimation_procedures(expdb)
