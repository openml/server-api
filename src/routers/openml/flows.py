import http.client
from typing import Annotated

from core.conversions import _str_to_num
from database.flows import get_flow as db_get_flow
from database.flows import get_flow_parameters, get_flow_subflows, get_flow_tags
from fastapi import APIRouter, Depends, HTTPException
from schemas.flows import Flow, Parameter
from sqlalchemy import Connection

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/{flow_id}")
def get_flow(flow_id: int, expdb: Annotated[Connection, Depends(expdb_connection)] = None) -> Flow:
    flow_rows = db_get_flow(flow_id, expdb)
    if not (flow := next(flow_rows, None)):
        raise HTTPException(status_code=http.client.NOT_FOUND, detail="Flow not found")

    parameter_rows = get_flow_parameters(flow_id, expdb)
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

    tags = get_flow_tags(flow_id, expdb)

    flow_rows = get_flow_subflows(flow_id, expdb)
    subflows = [
        {
            "identifier": flow.identifier,
            "flow": get_flow(flow_id=flow.child_id, expdb=expdb),
        }
        for flow in flow_rows
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
