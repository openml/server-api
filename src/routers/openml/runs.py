
from __future__ import annotations

import json
import logging
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import xmltodict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import database.flows
import database.processing
import database.runs
import database.tasks
from database.users import User
from routers.dependencies import expdb_connection, fetch_user
from schemas.runs import RunDetail, RunEvaluationResult, RunUploadResponse

if TYPE_CHECKING:
    from sqlalchemy import Connection

router = APIRouter(prefix="/runs", tags=["runs"])
log = logging.getLogger(__name__)





def _parse_run_xml(xml_bytes: bytes) -> dict:
    """Parse the run description XML uploaded by the client.

    Expected root element: <oml:run xmlns:oml="http://openml.org/openml">
    Required children: oml:task_id, oml:implementation_id (flow_id).
    Optional: oml:setup_string, oml:output_data, oml:parameter_setting.
    """
    try:
        raw = xmltodict.parse(xml_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail={"code": "530", "message": f"Invalid run description XML: {exc}"},
        ) from exc

    # Strip the namespace prefix so keys are consistent
    run_str = json.dumps(raw).replace("oml:", "")
    data: dict = json.loads(run_str)

    return data.get("run", {})





def _require_auth(user: User | None) -> User:
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.PRECONDITION_FAILED,
            detail={"code": "103", "message": "Authentication failed"},
        )
    return user


def _require_task(task_id: int, expdb: Connection) -> None:
    if not database.tasks.get(task_id, expdb):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"code": "201", "message": f"Unknown task: {task_id}"},
        )


def _require_flow(flow_id: int, expdb: Connection) -> None:
    if not database.flows.get(flow_id, expdb):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"code": "180", "message": f"Unknown flow: {flow_id}"},
        )





@router.post(
    "/",
    summary="Upload a run (predictions + description XML)",
    response_model=RunUploadResponse,
    status_code=HTTPStatus.CREATED,
)
async def upload_run(
    description: Annotated[UploadFile, File(description="Run description XML file")],
    predictions: Annotated[UploadFile, File(description="Predictions ARFF file")],
    user: Annotated[User | None, Depends(fetch_user)] = None,
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> RunUploadResponse:
    """Upload a new run.

    Accepts two multipart files:
    - **description**: XML file conforming to the OpenML run description schema
    - **predictions**: ARFF file with per-row predictions
      (columns: row_id, fold, repeat, prediction [, confidence.*])

    On success returns the new `run_id`. The run is immediately enqueued for
    server-side evaluation; metrics will be available after the worker processes it.
    """
    authenticated_user = _require_auth(user)

    xml_bytes = await description.read()
    run_xml = _parse_run_xml(xml_bytes)

    try:
        task_id = int(run_xml["task_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail={"code": "531", "message": "Missing or invalid task_id in run description"},
        ) from exc

    try:
        flow_id = int(run_xml["implementation_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail={
                "code": "532",
                "message": "Missing or invalid implementation_id (flow_id) in run description",
            },
        ) from exc

    setup_string: str | None = run_xml.get("setup_string")

    _require_task(task_id, expdb)
    _require_flow(flow_id, expdb)

    # Store the run row
    run_id = database.runs.create(
        task_id=task_id,
        flow_id=flow_id,
        uploader_id=authenticated_user.user_id,
        setup_string=setup_string,
        expdb=expdb,
    )

    # Persist the predictions file to disk so the worker can read it later
    from config import load_configuration  # noqa: PLC0415

    upload_dir: str = load_configuration().get("upload_dir", "/tmp/openml_runs")  # noqa: S108
    run_dir = Path(upload_dir) / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    predictions_bytes = await predictions.read()
    predictions_path = run_dir / "predictions.arff"
    predictions_path.write_bytes(predictions_bytes)

    # Enqueue for server-side evaluation
    database.processing.enqueue(run_id, expdb)

    log.info(
        "Run %d uploaded by user %d (task=%d, flow=%d).",
        run_id,
        authenticated_user.user_id,
        task_id,
        flow_id,
    )
    return RunUploadResponse(run_id=run_id)





@router.get(
    "/{run_id}",
    summary="Get run metadata and evaluation results",
)
def get_run(
    run_id: int,
    user: Annotated[User | None, Depends(fetch_user)] = None,  # noqa: ARG001
    expdb: Annotated[Connection, Depends(expdb_connection)] = None,
) -> RunDetail:
    """Return metadata and evaluation results for a single run."""
    run = database.runs.get(run_id, expdb)
    if run is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"code": "220", "message": f"Unknown run: {run_id}"},
        )

    tags = database.runs.get_tags(run_id, expdb)
    eval_rows = database.runs.get_evaluations(run_id, expdb)

    evaluations = []
    for row in eval_rows:
        per_fold: list[float] | None = None
        if row.array_data:
            try:
                per_fold = [float(v) for v in json.loads(row.array_data)]
            except (json.JSONDecodeError, ValueError):
                per_fold = None

        evaluations.append(
            RunEvaluationResult(
                function=row.function,
                value=row.value,
                per_fold=per_fold,
            ),
        )

    return RunDetail(
        id_=run.rid,
        task_id=run.task_id,
        flow_id=run.flow_id,
        uploader=run.uploader,
        upload_time=run.upload_time,
        setup_string=run.setup_string,
        tags=tags,
        evaluations=evaluations,
    )
