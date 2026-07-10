"""Defines endpoints relating to Estimation Procedures."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

import database.evaluations
from routers.dependencies import expdb_session
from routers.schemas.tasks import EstimationProcedure

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/estimationprocedure", tags=["estimationprocedure"])


@router.get("/list", response_model_exclude_none=True)
async def get_estimation_procedures(
    expdb: Annotated[AsyncSession, Depends(expdb_session)],
) -> list[EstimationProcedure]:
    """Return a list with descriptions of estimation procedures.

    Estimation procedures define how to evaluate a model, e.g., 5-repeated 2-fold cross-validation.
    """
    procedures = await database.evaluations.get_estimation_procedures(expdb)
    return list(procedures)
