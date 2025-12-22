from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection

import database.flows
from core.conversions import _str_to_num
from routers.dependencies import expdb_connection
from schemas.flows import Flow, Parameter

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/exists/{name}/{external_version}")
def flow_exists(
    name: str,
    external_version: str,
    expdb: Annotated[Connection, Depends(expdb_connection)],
) -> dict[Literal["flow_id"], int]:
    """Check if a Flow with the name and version exists, if so, return the flow id."""
    flow = database.flows.get_by_name(name=name, external_version=external_version, expdb=expdb)
    if flow is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Flow not found.",
        )
    return {"flow_id": flow.id}


@router.get("/{flow_id}")
def get_flow(flow_id: int, expdb: Annotated[Connection, Depends(expdb_connection)] = None) -> Flow:
    flow = database.flows.get(flow_id, expdb)
    if not flow:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Flow not found")

    parameter_rows = database.flows.get_parameters(flow_id, expdb)
    parameters = [
        Parameter(
            name=parameter.name,
            # PHP sets the default value to [], not sure where that comes from.
            # In the modern interface, `None` is used instead for now, but I think it might
            # make more sense to omit it if there is none.
            default_value=_str_to_num(parameter.default_value) if parameter.default_value else None,
            data_type=parameter.data_type,
            description=parameter.description,
        )
        for parameter in parameter_rows
    ]

    tags = database.flows.get_tags(flow_id, expdb)
    subflow_rows = database.flows.get_subflows(flow_id, expdb)
    subflows = [
        {
            "identifier": subflow.identifier,
            "flow": get_flow(flow_id=subflow.child_id, expdb=expdb),
        }
        for subflow in subflow_rows
    ]

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
        parameter=parameters,
        subflows=subflows,
        tag=tags,
    )
