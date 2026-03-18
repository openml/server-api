import contextlib
import re
from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.conftest import temporary_records
from tests.users import OWNER_USER, ApiKey


@pytest.fixture
def temporary_tags(
    expdb_test: AsyncConnection,
) -> Callable[..., AbstractAsyncContextManager[None]]:
    @contextlib.asynccontextmanager
    async def _temporary_tags(
        tags: Iterable[str], setup_id: int, *, persist: bool = False
    ) -> AsyncGenerator[None]:
        insert_queries = [
            (
                "INSERT INTO setup_tag(`id`,`tag`,`uploader`) VALUES (:setup_id, :tag, :user_id);",
                {"setup_id": setup_id, "tag": tag, "user_id": OWNER_USER.user_id},
            )
            for tag in tags
        ]
        delete_queries = [
            (
                "DELETE FROM setup_tag WHERE `id`=:setup_id AND `tag`=:tag",
                {"setup_id": setup_id, "tag": tag},
            )
            for tag in tags
        ]
        async with temporary_records(
            connection=expdb_test,
            insert_queries=insert_queries,
            delete_queries=delete_queries,
            persist=persist,
        ):
            yield

    return _temporary_tags


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "non-owner", "tag owner"],
)
@pytest.mark.parametrize(
    "other_tags",
    [[], ["some_other_tag"], ["foo_some_other_tag", "bar_some_other_tag"]],
    ids=["none", "one tag", "two tags"],
)
async def test_setup_untag_response_is_identical_when_tag_exists(
    api_key: str,
    other_tags: list[str],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"

    all_tags = [tag, *other_tags]
    async with temporary_tags(tags=all_tags, setup_id=setup_id, persist=True):
        original = await php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

    # expdb_test transaction shared with Python API,
    # no commit needed and rolled back at the end of the test
    async with temporary_tags(tags=all_tags, setup_id=setup_id):
        new = await py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    if new.status_code == HTTPStatus.OK:
        assert original.status_code == new.status_code
        original_untag = original.json()["setup_untag"]
        new_untag = new.json()["setup_untag"]
        assert original_untag["id"] == new_untag["id"]
        if tags := original_untag.get("tag"):
            if isinstance(tags, str):
                assert tags == new_untag["tag"][0]
            else:
                assert tags == new_untag["tag"]
        else:
            assert new_untag["tag"] == []
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


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER],
    ids=["Administrator", "non-owner"],
)
@pytest.mark.parametrize(
    "other_tags",
    [[], ["some_other_tag"], ["foo_some_other_tag", "bar_some_other_tag"]],
    ids=["none", "one tag", "two tags"],
)
async def test_setup_tag_response_is_identical_when_tag_doesnt_exist(  # noqa: PLR0913
    api_key: str,
    other_tags: list[str],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"

    async with temporary_tags(tags=other_tags, setup_id=setup_id, persist=True):
        original = await php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

        await expdb_test.execute(
            text("DELETE FROM setup_tag WHERE `id`=:setup_id AND `tag`=:tag"),
            parameters={"setup_id": setup_id, "tag": tag},
        )
        await expdb_test.commit()

    async with temporary_tags(tags=other_tags, setup_id=setup_id):
        new = await py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    assert new.status_code == HTTPStatus.OK
    assert original.status_code == new.status_code
    original_tag = original.json()["setup_tag"]
    new_tag = new.json()["setup_tag"]
    assert original_tag["id"] == new_tag["id"]
    if tags := original_tag.get("tag"):
        if isinstance(tags, str):
            assert tags == new_tag["tag"][0]
        else:
            assert set(tags) == set(new_tag["tag"])
    else:
        assert new_tag["tag"] == []


async def test_setup_tag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    original = await php_api.post(
        "/setup/tag",
        data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
    )

    new = await py_api.post(
        f"/setup/tag?api_key={api_key}",
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


async def test_setup_tag_response_is_identical_tag_already_exists(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    async with temporary_tags(tags=[tag], setup_id=setup_id, persist=True):
        original = await php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

        # In Python, since PHP committed it, it's also there for Python test context
        new = await py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    assert original.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert new.status_code == HTTPStatus.CONFLICT
    assert original.json()["error"]["message"] == "Entity already tagged by this tag."
    assert new.json()["detail"] == f"Setup {setup_id} already has tag {tag!r}."


async def test_get_setup_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999

    original = await php_api.get(f"/setup/{setup_id}")
    new = await py_api.get(f"/setup/{setup_id}")

    assert original.status_code == HTTPStatus.PRECONDITION_FAILED
    assert new.status_code == HTTPStatus.NOT_FOUND
    assert original.json()["error"]["message"] == "Unknown setup"
    assert original.json()["error"]["code"] == new.json()["code"]


@pytest.mark.parametrize("setup_id", [1, 48])
async def test_get_setup_response_is_identical(
    setup_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    original = await php_api.get(f"/setup/{setup_id}")
    new = await py_api.get(f"/setup/{setup_id}")

    assert original.status_code == HTTPStatus.OK
    assert new.status_code == HTTPStatus.OK

    assert original.json() == new.json()
