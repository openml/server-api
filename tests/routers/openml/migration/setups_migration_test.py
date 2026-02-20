from http import HTTPStatus

import httpx
import pytest
from starlette.testclient import TestClient

from tests.users import ApiKey


@pytest.mark.parametrize(
    "setup_id",
    [1, 999999],
    ids=["existing setup", "unknown setup"],
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["totally_new_tag_for_migration_testing"],
)
def test_setup_untag_response_is_identical(
    setup_id: int,
    tag: str,
    api_key: str,
    py_api: TestClient,
    php_api: httpx.Client,
) -> None:
    if setup_id == 1:
        php_api.post(
            "/setup/tag",
            data={"api_key": ApiKey.SOME_USER, "tag": tag, "setup_id": setup_id},
        )

    original = php_api.post(
        "/setup/untag",
        data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
    )

    if original.status_code == HTTPStatus.OK:
        php_api.post(
            "/setup/tag",
            data={"api_key": ApiKey.SOME_USER, "tag": tag, "setup_id": setup_id},
        )

    new = py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": setup_id, "tag": tag},
    )

    assert original.status_code == new.status_code

    if new.status_code != HTTPStatus.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    original_json = original.json()
    new_json = new.json()

    assert original_json == new_json
