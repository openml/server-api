"""Tests for database layer of runs."""

from sqlalchemy.ext.asyncio import AsyncConnection  # noqa: TC002

import database.runs
import database.tasks
import database.users

_RUN_ID = 24
_MISSING_RUN_ID = 999_999_999
_MISSING_USER_ID = 999_999_999
_RUN_UPLOADER_ID = 1159
_RUN_TASK_ID = 115
_RUN_SETUP_ID = 2
_RUN_DATASET_ID = 20
_DESCRIPTION_FILE_ID = 182
_PREDICTIONS_FILE_ID = 183


async def test_db_get_run_exists(expdb_test: AsyncConnection) -> None:
    """database.runs.get returns a row for run 24."""
    row = await database.runs.get(_RUN_ID, expdb_test)
    assert row is not None
    assert row.rid == _RUN_ID
    assert row.uploader == _RUN_UPLOADER_ID
    assert row.task_id == _RUN_TASK_ID
    assert row.setup == _RUN_SETUP_ID
    assert row.error_message is None  # no error for this run


async def test_db_get_run_missing(expdb_test: AsyncConnection) -> None:
    """database.runs.get returns None for a non-existent run."""
    row = await database.runs.get(_MISSING_RUN_ID, expdb_test)
    assert row is None


async def test_db_exist_true(expdb_test: AsyncConnection) -> None:
    """database.runs.exist returns True for run 24."""
    assert await database.runs.exist(_RUN_ID, expdb_test) is True


async def test_db_exist_false(expdb_test: AsyncConnection) -> None:
    """database.runs.exist returns False for a missing run."""
    assert await database.runs.exist(_MISSING_RUN_ID, expdb_test) is False


async def test_db_get_tags(expdb_test: AsyncConnection) -> None:
    """database.runs.get_tags returns expected tags for run 24."""
    tags = await database.runs.get_tags(_RUN_ID, expdb_test)
    assert isinstance(tags, list)
    assert "openml-python" in tags


async def test_db_get_input_data(expdb_test: AsyncConnection) -> None:
    """database.runs.get_input_data returns did=20 (diabetes) for run 24."""
    rows = await database.runs.get_input_data(_RUN_ID, expdb_test)
    assert len(rows) >= 1
    dids = [r.did for r in rows]
    assert _RUN_DATASET_ID in dids


async def test_db_get_output_files(expdb_test: AsyncConnection) -> None:
    """database.runs.get_output_files returns description and predictions files."""
    rows = await database.runs.get_output_files(_RUN_ID, expdb_test)
    file_map = {r.field: r.file_id for r in rows}
    assert file_map.get("description") == _DESCRIPTION_FILE_ID
    assert file_map.get("predictions") == _PREDICTIONS_FILE_ID


async def test_db_get_evaluations(expdb_test: AsyncConnection) -> None:
    """database.runs.get_evaluations returns metrics including area_under_roc_curve."""
    rows = await database.runs.get_evaluations(_RUN_ID, expdb_test, evaluation_engine_ids=[1])
    assert len(rows) > 0
    names = {r.name for r in rows}
    assert "area_under_roc_curve" in names


async def test_db_get_evaluations_empty_engine_list(expdb_test: AsyncConnection) -> None:
    """get_evaluations with no engine IDs returns an empty list (not an error)."""
    rows = await database.runs.get_evaluations(_RUN_ID, expdb_test, evaluation_engine_ids=[])
    assert rows == []


async def test_db_get_task_type(expdb_test: AsyncConnection) -> None:
    """database.runs.get_task_type returns 'Supervised Classification' for task 115."""
    task_type = await database.tasks.get_task_type_name(_RUN_TASK_ID, expdb_test)
    assert task_type == "Supervised Classification"


async def test_db_get_task_evaluation_measure_missing(expdb_test: AsyncConnection) -> None:
    """get_task_evaluation_measure returns None (not '') when absent."""
    measure = await database.tasks.get_task_evaluation_measure(_RUN_TASK_ID, expdb_test)
    assert measure is None


async def test_db_get_uploader_name(user_test: AsyncConnection) -> None:
    """database.runs.get_uploader_name returns 'Cynthia Glover' for user 1159."""
    user = await database.users.get_user(user_id=_RUN_UPLOADER_ID, connection=user_test)
    assert user is not None
    assert user.full_name == "Cynthia Glover"
    assert user.user_id == _RUN_UPLOADER_ID


async def test_db_get_uploader_name_missing(user_test: AsyncConnection) -> None:
    """get_uploader_name returns None for a non-existent user."""
    user = await database.users.get_user(user_id=_MISSING_USER_ID, connection=user_test)
    assert user is None
