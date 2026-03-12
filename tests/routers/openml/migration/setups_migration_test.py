import contextlib
import re
from collections.abc import AsyncGenerator
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.users import OWNER_USER, ApiKey


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "non-owner", "tag owner"],
)
async def test_setup_untag_response_is_identical_when_tag_exists(
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"

    @contextlib.asynccontextmanager
    async def temporary_tag() -> AsyncGenerator[None]:
        await expdb_test.execute(
            text(
                "INSERT INTO setup_tag(`id`,`tag`,`uploader`) VALUES (:setup_id, :tag, :user_id);"
            ),
            parameters={"setup_id": setup_id, "tag": tag, "user_id": OWNER_USER.user_id},
        )
        await expdb_test.commit()
        yield
        await expdb_test.execute(
            text("DELETE FROM setup_tag WHERE `id`=:setup_id AND `tag`=:tag"),
            parameters={"setup_id": setup_id, "tag": tag},
        )
        await expdb_test.commit()

    async with temporary_tag():
        original = await php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

    # expdb_test transaction shared with Python API,
    # no commit needed and rolled back at the end of the test
    await expdb_test.execute(
        text("INSERT INTO setup_tag(`id`,`tag`,`uploader`) VALUES (:setup_id, :tag, :user_id);"),
        parameters={"setup_id": setup_id, "tag": tag, "user_id": OWNER_USER.user_id},
    )

    new = await py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": setup_id, "tag": tag},
    )

    if new.status_code == HTTPStatus.OK:
        assert original.status_code == new.status_code
        assert original.json() == new.json()
        return

    code, message = original.json()["error"].values()
    assert original.status_code == HTTPStatus.PRECONDITION_FAILED
    assert new.status_code == HTTPStatus.FORBIDDEN
    assert code == new.json()["code"]
    assert message == "Tag is not owned by you"
    assert re.match(
        r"You may not remove tag \S+ of setup \d+ because it was not created by you.",
        new.json()["detail"],
    )


async def test_setup_untag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    original = await php_api.post(
        "/setup/untag",
        data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
    )

    new = await py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": setup_id, "tag": tag},
    )

    assert original.status_code == HTTPStatus.PRECONDITION_FAILED
    assert new.status_code == HTTPStatus.NOT_FOUND
    assert original.json()["error"]["message"] == "Entity not found."
    assert original.json()["error"]["code"] == new.json()["code"]
    assert re.match(
        r"Setup \d+ not found.",
        new.json()["detail"],
    )


async def test_setup_untag_response_is_identical_tag_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    original = await php_api.post(
        "/setup/untag",
        data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
    )

    new = await py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": setup_id, "tag": tag},
    )

    assert original.status_code == HTTPStatus.PRECONDITION_FAILED
    assert new.status_code == HTTPStatus.NOT_FOUND
    assert original.json()["error"]["code"] == new.json()["code"]
    assert original.json()["error"]["message"] == "Tag not found."
    assert re.match(
        r"Setup \d+ does not have tag '\S+'.",
        new.json()["detail"],
    )
