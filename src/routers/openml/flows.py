import http.client
from typing import Annotated

from core.conversions import _str_to_num
from fastapi import APIRouter, Depends, HTTPException
from schemas.flows import Flow, Parameter
from sqlalchemy import Connection, text

from routers.dependencies import expdb_connection

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/{flow_id}")
def get_flow(flow_id: int, expdb: Annotated[Connection, Depends(expdb_connection)] = None) -> Flow:
    flow_rows = expdb.execute(
        text(
            """
            SELECT *, uploadDate as upload_date
            FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    if not (flow := next(flow_rows, None)):
        raise HTTPException(status_code=http.client.NOT_FOUND, detail="Flow not found")

    parameter_rows = expdb.execute(
        text(
            """
            SELECT *, defaultValue as default_value, dataType as data_type
            FROM input
            WHERE implementation_id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
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

    tag_rows = expdb.execute(
        text(
            """
            SELECT tag
            FROM implementation_tag
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
    tags = [tag.tag for tag in tag_rows]

    flow_rows = expdb.execute(
        text(
            """
            SELECT child as child_id, identifier
            FROM implementation_component
            WHERE parent = :flow_id
            """,
        ),
        parameters={"flow_id": flow_id},
    )
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
