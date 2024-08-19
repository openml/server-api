from typing import Annotated, Iterable

from fastapi import APIRouter, Depends
from sqlalchemy import Connection

import database.evaluations
from routers.dependencies import expdb_connection
from schemas.datasets.openml import EstimationProcedure

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
def get_estimation_procedures(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> Iterable[EstimationProcedure]:
    return database.evaluations.get_estimation_procedures(expdb)
