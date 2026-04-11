import asyncio
import contextlib
import re
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.conversions import nested_remove_values, nested_str_to_num
from tests.conftest import temporary_records
from tests.users import OWNER_USER, ApiKey


@pytest.fixture
def temporary_tags(
    expdb_test: AsyncConnection,
) -> Callable[..., AbstractAsyncContextManager[None]]:
    @contextlib.asynccontextmanager
    async def _temporary_tags(
        tags: Iterable[str], setup_id: int, *, persist: bool = False
    ) -> AsyncIterator[None]:
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


@pytest.mark.mut
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
        php_response = await php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

    # expdb_test transaction shared with Python API,
    # no commit needed and rolled back at the end of the test
    async with temporary_tags(tags=all_tags, setup_id=setup_id):
        py_response = await py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    if py_response.status_code == HTTPStatus.OK:
        assert py_response.status_code == php_response.status_code
        php_untag = php_response.json()["setup_untag"]
        py_untag = py_response.json()["setup_untag"]
        assert py_untag["id"] == php_untag["id"]
        if tags := php_untag.get("tag"):
            if isinstance(tags, str):
                assert py_untag["tag"][0] == tags
            else:
                assert py_untag["tag"] == tags
        else:
            assert py_untag["tag"] == []
        return

    code, message = php_response.json()["error"].values()
    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.FORBIDDEN
    assert py_response.json()["code"] == code
    assert message == "Tag is not owned by you"
    assert re.match(
        r"You may not remove tag \S+ of setup \d+ because it was not created by you.",
        py_response.json()["detail"],
    )


async def test_setup_untag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        ),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert php_response.json()["error"]["message"] == "Entity not found."
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert re.match(
        r"Setup \d+ not found.",
        py_response.json()["detail"],
    )


async def test_setup_untag_response_is_identical_tag_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        ),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert php_response.json()["error"]["message"] == "Tag not found."
    assert re.match(
        r"Setup \d+ does not have tag '\S+'.",
        py_response.json()["detail"],
    )


@pytest.mark.mut
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
        php_response = await php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

        await expdb_test.execute(
            text("DELETE FROM setup_tag WHERE `id`=:setup_id AND `tag`=:tag"),
            parameters={"setup_id": setup_id, "tag": tag},
        )
        await expdb_test.commit()

    async with temporary_tags(tags=other_tags, setup_id=setup_id):
        py_response = await py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    assert py_response.status_code == HTTPStatus.OK
    assert py_response.status_code == php_response.status_code
    php_tag = php_response.json()["setup_tag"]
    py_tag = py_response.json()["setup_tag"]
    assert py_tag["id"] == php_tag["id"]
    if tags := php_tag.get("tag"):
        if isinstance(tags, str):
            assert py_tag["tag"][0] == tags
        else:
            assert set(py_tag["tag"]) == set(tags)
    else:
        assert py_tag["tag"] == []


async def test_setup_tag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        ),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert php_response.json()["error"]["message"] == "Entity not found."
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert re.match(
        r"Setup \d+ not found.",
        py_response.json()["detail"],
    )


@pytest.mark.mut
async def test_setup_tag_response_is_identical_tag_already_exists(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    async with temporary_tags(tags=[tag], setup_id=setup_id, persist=True):
        # Both APIs can be tested in parallel since the tag is already persisted
        php_response, py_response = await asyncio.gather(
            php_api.post(
                "/setup/tag",
                data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
            ),
            py_api.post(
                f"/setup/tag?api_key={api_key}",
                json={"setup_id": setup_id, "tag": tag},
            ),
        )

    assert php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert py_response.status_code == HTTPStatus.CONFLICT
    assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
    assert py_response.json()["detail"] == f"Setup {setup_id} already has tag {tag!r}."


async def test_get_setup_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999

    php_response, py_response = await asyncio.gather(
        php_api.get(f"/setup/{setup_id}"),
        py_api.get(f"/setup/{setup_id}"),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert php_response.json()["error"]["message"] == "Unknown setup"
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert py_response.json()["detail"] == f"Setup {setup_id} not found."


@pytest.mark.parametrize("setup_id", range(1, 125))
async def test_get_setup_response_is_identical(
    setup_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    php_response, py_response = await asyncio.gather(
        php_api.get(f"/setup/{setup_id}"),
        py_api.get(f"/setup/{setup_id}"),
    )

    if php_response.status_code == HTTPStatus.PRECONDITION_FAILED:
        assert py_response.status_code == HTTPStatus.NOT_FOUND
        return

    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == HTTPStatus.OK

    php_json = php_response.json()

    # PHP returns integer fields as strings. To compare, we recursively convert string digits
    # to integers.
    # PHP also returns `[]` instead of null for empty string optional fields, which Python omits.
    php_json = nested_str_to_num(php_json)
    php_json = nested_remove_values(php_json, values=[[], None])

    py_json = nested_str_to_num(py_response.json())
    py_json = nested_remove_values(py_json, values=[[], None])

    assert py_json == php_json
