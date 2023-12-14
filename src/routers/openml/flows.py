import http.client
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from schemas.flows import Flow
from sqlalchemy import Connection, text

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/{flow_id}")
def get_flow(flow_id: int, expdb: Annotated[Connection, Depends(expdb_connection)] = None) -> Flow:
    rows = expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    if not (flow := next(rows, None)):
        raise HTTPException(status_code=http.client.NOT_FOUND, detail="Flow not found")

    return Flow(
        id_=flow.id,
        uploader=flow.uploader,
        name=flow.name,
        class_name=flow.class_name,
        version=flow.version,
        external_version=flow.external_version,
        description=flow.description,
        upload_date=flow.upload_date,
        language=flow.language,
        dependencies=flow.dependencies,
        parameter=[
            {
                "name": "-do-not-check-capabilities",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier capabilities are not checked before classifier is built\n\t(use with caution).",  # noqa: E501
            },
            {
                "name": "batch-size",
                "data_type": "option",
                "default_value": [],
                "description": "The desired batch size for batch prediction  (default 100).",
            },
            {
                "name": "num-decimal-places",
                "data_type": "option",
                "default_value": [],
                "description": "The number of decimal places for the output of numbers in the model (default 2).",  # noqa: E501
            },
            {
                "name": "output-debug-info",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier is run in debug mode and\n\tmay output additional info to the console",  # noqa: E501
            },
        ],
        subflows=[],
        tag=["OpenmlWeka", "weka"],
    )
