from http import HTTPStatus
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import Connection

import database.flows
from core.conversions import _str_to_num
from database.users import User, UserGroup
from routers.dependencies import expdb_connection, fetch_user
from routers.types import SystemString64
from schemas.flows import Flow, Parameter, Subflow

router = APIRouter(prefix="/flows", tags=["flows"])


@router.post(path="/tag")
def tag_flow(
    flow_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        )
    tags = database.flows.get_tags(flow_id, expdb)
    if tag.casefold() in [t.casefold() for t in tags]:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "473",
                "message": "Entity already tagged by this tag.",
                "additional_information": f"id={flow_id}; tag={tag}",
            },
        )
    database.flows.tag(flow_id, tag, user_id=user.user_id, connection=expdb)
    return {"flow_tag": {"id": str(flow_id), "tag": [*tags, tag]}}


@router.post(path="/untag")
def untag_flow(
    flow_id: Annotated[int, Body()],
    tag: Annotated[str, SystemString64],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> dict[str, dict[str, Any]]:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        )
    existing = database.flows.get_tag(flow_id, tag, expdb)
    if existing is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "477",
                "message": "Tag not found.",
                "additional_information": f"id={flow_id}; tag={tag}",
            },
        )
    if existing.uploader != user.user_id and UserGroup.ADMIN not in user.groups:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail={
                "code": "478",
                "message": "Tag is not owned by you.",
                "additional_information": f"id={flow_id}; tag={tag}",
            },
        )
    database.flows.delete_tag(flow_id, tag, expdb)
    tags = database.flows.get_tags(flow_id, expdb)
    return {"flow_tag": {"id": str(flow_id), "tag": tags}}


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
        Subflow(
            identifier=subflow.identifier,
            flow=get_flow(flow_id=subflow.child_id, expdb=expdb),
        )
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
