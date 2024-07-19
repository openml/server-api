from typing import Annotated, Iterable

import database.evaluations
from fastapi import APIRouter, Depends
from schemas.datasets.openml import EstimationProcedure
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
def get_estimation_procedures(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> Iterable[EstimationProcedure]:
    return database.evaluations.get_estimation_procedures(expdb)
