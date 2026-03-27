from datetime import UTC, datetime
from http import HTTPStatus

import httpx
import pytest

from tests.users import ApiKey


@pytest.mark.mut
async def test_create_task_study(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        f"/studies?api_key={ApiKey.SOME_USER}",
        json={
            "name": "Test Study",
            "alias": "test-study",
            "main_entity_type": "task",
            "description": "A test study",
            "tasks": [1, 2, 3],
            "runs": [],
        },
    )
    assert response.status_code == HTTPStatus.OK
    new = response.json()
    assert "study_id" in new
    study_id = new["study_id"]
    assert isinstance(study_id, int)

    study = await py_api.get(f"/studies/{study_id}")
    assert study.status_code == HTTPStatus.OK
    expected = {
        "id": study_id,
        "alias": "test-study",
        "main_entity_type": "task",
        "name": "Test Study",
        "description": "A test study",
        "visibility": "public",
        "status": "in_preparation",
        "creator": 2,
        "data_ids": [1, 1, 1],
        "task_ids": [1, 2, 3],
        "run_ids": [],
        "flow_ids": [],
        "setup_ids": [],
    }
    new_study = study.json()

    creation_date = datetime.fromisoformat(new_study.pop("creation_date"))
    assert creation_date.date() == datetime.now(UTC).date()
    assert new_study == expected
