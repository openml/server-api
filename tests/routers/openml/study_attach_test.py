from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import StudyConflictError
from schemas.study import StudyType
from tests.users import ApiKey


async def _attach_tasks_to_study(
    study_id: int,
    task_ids: list[int],
    api_key: str,
    py_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
) -> httpx.Response:
    # Adding requires the study to be in preparation,
    # but the current snapshot has no in-preparation studies.
    await expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    return await py_api.post(
        f"/studies/attach?api_key={api_key}",
        json={"study_id": study_id, "entity_ids": task_ids},
    )


@pytest.mark.mut
async def test_attach_task_to_study(py_api: httpx.AsyncClient, expdb_test: AsyncConnection) -> None:
    response = await _attach_tasks_to_study(
        study_id=1,
        task_ids=[2, 3, 4],
        api_key=ApiKey.ADMIN,
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == {"study_id": 1, "main_entity_type": StudyType.TASK}


@pytest.mark.mut
async def test_attach_task_to_study_needs_owner(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    await expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = await _attach_tasks_to_study(
        study_id=1,
        task_ids=[2, 3, 4],
        api_key=ApiKey.OWNER_USER,
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.FORBIDDEN, response.content


@pytest.mark.mut
async def test_attach_task_to_study_already_linked_raises(
    py_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
) -> None:
    await expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = await _attach_tasks_to_study(
        study_id=1,
        task_ids=[1, 3, 4],
        api_key=ApiKey.ADMIN,
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.CONFLICT, response.content
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == StudyConflictError.uri
    assert error["detail"] == "Task 1 is already attached to study 1."


@pytest.mark.mut
async def test_attach_task_to_study_but_task_not_exist_raises(
    py_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
) -> None:
    await expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = await _attach_tasks_to_study(
        study_id=1,
        task_ids=[80123, 78914],
        api_key=ApiKey.ADMIN,
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == StudyConflictError.uri
    assert error["detail"] == "One or more of the tasks do not exist."
