"""Tests for the POST /datasets/status/update endpoint."""

from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import DatasetAdminOnlyError, DatasetNotOwnedError
from routers.openml.datasets import update_dataset_status
from schemas.datasets.openml import DatasetStatus
from tests import constants
from tests.users import ADMIN_USER, SOME_USER


async def test_update_status_via_api(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        "/datasets/status/update",
        json={"dataset_id": 1, "status": "active"},
    )
    # Without authentication, we expect 401 — confirms the route is wired up.
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.mut
@pytest.mark.parametrize("dataset_id", [3, 4])
async def test_dataset_status_update_active_to_deactivated(
    dataset_id: int, expdb_test: AsyncConnection
) -> None:
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.DEACTIVATED,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.DEACTIVATED}


@pytest.mark.mut
async def test_dataset_status_update_in_preparation_to_active(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.IN_PREPARATION_ID))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.ACTIVE,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.ACTIVE}


@pytest.mark.mut
async def test_dataset_status_update_in_preparation_to_deactivated(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.IN_PREPARATION_ID))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.DEACTIVATED,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.DEACTIVATED}


@pytest.mark.mut
async def test_dataset_status_update_deactivated_to_active(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.DEACTIVATED_DATASETS))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.ACTIVE,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.ACTIVE}


@pytest.mark.parametrize("dataset_id", [1, 33, 131])
async def test_dataset_status_non_admin_cannot_activate(
    dataset_id: int,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetAdminOnlyError):
        await update_dataset_status(
            dataset_id=dataset_id,
            status=DatasetStatus.ACTIVE,
            user=SOME_USER,
            expdb=expdb_test,
        )


@pytest.mark.parametrize("dataset_id", [1, 2])
async def test_dataset_status_non_owner_cannot_deactivate(
    dataset_id: int,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetNotOwnedError):
        await update_dataset_status(
            dataset_id=dataset_id,
            status=DatasetStatus.DEACTIVATED,
            user=SOME_USER,
            expdb=expdb_test,
        )
