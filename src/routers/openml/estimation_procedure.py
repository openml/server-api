from typing import Annotated, Iterable

from database.evaluations import get_estimation_procedures as db_get_estimation_procedures
from fastapi import APIRouter, Depends
from schemas.datasets.openml import EstimationProcedure
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
def get_estimation_procedures(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> Iterable[EstimationProcedure]:
    return db_get_estimation_procedures(expdb)
