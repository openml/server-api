"""Defines endpoints relating to Evaluation Measures."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

import database.evaluations
from routers.dependencies import expdb_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/evaluationmeasure", tags=["evaluationmeasure"])


@router.get("/list")
async def get_evaluation_measures(
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
) -> list[str]:
    """Return a list of evaluation measure names.

    Evaluation measures are any function that is computed over either predictions
    or may otherwise be provided as run metadata. Examples include "area_under_roc_curve",
    "recall", or "usercpu_time_millis". This may be used for filtering or ordering evaluations.

    There are no detailed descriptions available for these measures at this time.
    """
    functions = await database.evaluations.get_math_functions(
        function_type="EvaluationFunction",
        session=expdb,
    )
    return [function.name for function in functions]
