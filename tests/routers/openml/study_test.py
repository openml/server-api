from datetime import datetime
from http import HTTPStatus

import httpx
from sqlalchemy import Connection, text
from starlette.testclient import TestClient

from schemas.study import StudyType


def test_get_task_study_by_id(py_api: TestClient) -> None:
    response = py_api.get("/studies/1")
    assert response.status_code == HTTPStatus.OK
    expected = {
        "id": 1,
        "alias": "OpenML100",
        "main_entity_type": "task",
        "name": "OpenML100",
        "description": "OpenML100 equivalent on capa",
        "visibility": "public",
        "status": "active",
        "creation_date": "2019-02-25T17:15:01",
        "creator": 1,
        "data_ids": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            38,
            39,
            40,
            41,
            42,
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            59,
            60,
            61,
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
            70,
            71,
            72,
            73,
            74,
            75,
            76,
            77,
            78,
            79,
            80,
            81,
            82,
            83,
            84,
            85,
            86,
            87,
            88,
            89,
            90,
            91,
            92,
            93,
            94,
            95,
            96,
            97,
            98,
            99,
            100,
        ],
        "task_ids": [
            1,
            7,
            13,
            19,
            25,
            31,
            37,
            43,
            49,
            55,
            61,
            67,
            73,
            79,
            85,
            91,
            97,
            103,
            109,
            115,
            121,
            127,
            133,
            139,
            145,
            151,
            157,
            163,
            169,
            175,
            181,
            187,
            193,
            199,
            205,
            211,
            217,
            223,
            229,
            235,
            241,
            247,
            253,
            259,
            265,
            271,
            277,
            283,
            289,
            295,
            301,
            307,
            313,
            319,
            325,
            331,
            337,
            343,
            349,
            355,
            361,
            367,
            373,
            379,
            385,
            391,
            397,
            403,
            409,
            415,
            421,
            427,
            433,
            439,
            445,
            451,
            457,
            463,
            469,
            475,
            481,
            487,
            493,
            499,
            505,
            511,
            517,
            523,
            529,
            535,
            541,
            547,
            553,
            559,
            565,
            571,
            577,
            583,
            589,
            595,
        ],
        "run_ids": [],
        "flow_ids": [],
        "setup_ids": [],
    }
    assert response.json() == expected


def test_get_task_study_by_alias(py_api: TestClient) -> None:
    response = py_api.get("/studies/OpenML100")
    assert response.status_code == HTTPStatus.OK
    expected = {
        "id": 1,
        "alias": "OpenML100",
        "main_entity_type": "task",
        "name": "OpenML100",
        "description": "OpenML100 equivalent on capa",
        "visibility": "public",
        "status": "active",
        "creation_date": "2019-02-25T17:15:01",
        "creator": 1,
        "data_ids": [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            38,
            39,
            40,
            41,
            42,
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            59,
            60,
            61,
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
            70,
            71,
            72,
            73,
            74,
            75,
            76,
            77,
            78,
            79,
            80,
            81,
            82,
            83,
            84,
            85,
            86,
            87,
            88,
            89,
            90,
            91,
            92,
            93,
            94,
            95,
            96,
            97,
            98,
            99,
            100,
        ],
        "task_ids": [
            1,
            7,
            13,
            19,
            25,
            31,
            37,
            43,
            49,
            55,
            61,
            67,
            73,
            79,
            85,
            91,
            97,
            103,
            109,
            115,
            121,
            127,
            133,
            139,
            145,
            151,
            157,
            163,
            169,
            175,
            181,
            187,
            193,
            199,
            205,
            211,
            217,
            223,
            229,
            235,
            241,
            247,
            253,
            259,
            265,
            271,
            277,
            283,
            289,
            295,
            301,
            307,
            313,
            319,
            325,
            331,
            337,
            343,
            349,
            355,
            361,
            367,
            373,
            379,
            385,
            391,
            397,
            403,
            409,
            415,
            421,
            427,
            433,
            439,
            445,
            451,
            457,
            463,
            469,
            475,
            481,
            487,
            493,
            499,
            505,
            511,
            517,
            523,
            529,
            535,
            541,
            547,
            553,
            559,
            565,
            571,
            577,
            583,
            589,
            595,
        ],
        "run_ids": [],
        "flow_ids": [],
        "setup_ids": [],
    }
    assert response.json() == expected


def test_create_task_study(py_api: TestClient) -> None:
    response = py_api.post(
        "/studies?api_key=00000000000000000000000000000000",
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

    study = py_api.get(f"/studies/{study_id}")
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

    creation_date = datetime.strptime(
        new_study.pop("creation_date"),
        "%Y-%m-%dT%H:%M:%S",
    )
    assert creation_date.date() == datetime.now().date()
    assert new_study == expected


def _attach_tasks_to_study(
    study_id: int,
    task_ids: list[int],
    api_key: str,
    py_api: TestClient,
    expdb_test: Connection,
) -> httpx.Response:
    # Adding requires the study to be in preparation,
    # but the current snapshot has no in-preparation studies.
    expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    return py_api.post(
        f"/studies/attach?api_key={api_key}",
        json={"study_id": study_id, "entity_ids": task_ids},
    )


def test_attach_task_to_study(py_api: TestClient, expdb_test: Connection) -> None:
    response = _attach_tasks_to_study(
        study_id=1,
        task_ids=[2, 3, 4],
        api_key="AD000000000000000000000000000000",
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"study_id": 1, "main_entity_type": StudyType.TASK}


def test_attach_task_to_study_needs_owner(py_api: TestClient, expdb_test: Connection) -> None:
    expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = _attach_tasks_to_study(
        study_id=1,
        task_ids=[2, 3, 4],
        api_key="00000000000000000000000000000000",
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_attach_task_to_study_already_linked_raises(
    py_api: TestClient,
    expdb_test: Connection,
) -> None:
    expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = _attach_tasks_to_study(
        study_id=1,
        task_ids=[1, 3, 4],
        api_key="AD000000000000000000000000000000",
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"detail": "Task 1 is already attached to study 1."}


def test_attach_task_to_study_but_task_not_exist_raises(
    py_api: TestClient,
    expdb_test: Connection,
) -> None:
    expdb_test.execute(text("UPDATE study SET status = 'in_preparation' WHERE id = 1"))
    response = _attach_tasks_to_study(
        study_id=1,
        task_ids=[80123, 78914],
        api_key="AD000000000000000000000000000000",
        py_api=py_api,
        expdb_test=expdb_test,
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {"detail": "One or more of the tasks do not exist."}
