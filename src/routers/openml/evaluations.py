from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

import database.evaluations
from routers.dependencies import expdb_connection

router = APIRouter(prefix="/evaluationmeasure", tags=["evaluationmeasure"])


@router.get("/list")
async def get_evaluation_measures(expdb: Annotated[AsyncConnection, Depends(expdb_connection)]) -> list[str]:
    functions = await database.evaluations.get_math_functions(
        function_type="EvaluationFunction",
        connection=expdb,
    )
    return [function.name for function in functions]
