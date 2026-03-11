from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Connection

import database.evaluations
from routers.dependencies import expdb_connection
from schemas.datasets.openml import EstimationProcedure

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
def get_estimation_procedures(
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> list[EstimationProcedure]:
    # `list` required for exclusion of none: https://github.com/fastapi/fastapi/discussions/15089
    return list(database.evaluations.get_estimation_procedures(expdb))
