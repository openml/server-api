from typing import Annotated

import database.evaluations
from fastapi import APIRouter, Depends
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/evaluationmeasure", tags=["evaluationmeasure"])


@router.get("/list")
def get_evaluation_measures(expdb: Annotated[Connection, Depends(expdb_connection)]) -> list[str]:
    functions = database.evaluations.get_math_functions(
        function_type="EvaluationFunction",
        connection=expdb,
    )
    return [function.name for function in functions]
