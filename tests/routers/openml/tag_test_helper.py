import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from core.conversions import nested_remove_single_element_list

if TYPE_CHECKING:
    import httpx


async def assert_tag_response_is_identical(  # noqa: PLR0913
    identifier: int,
    tag: str,
    api_key: str,
    entity: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    php_alias = "data" if entity == "dataset" else entity
    # PHP request must happen first to check state, can't parallelize
    php_response = await php_api.post(
        f"/{php_alias}/tag",
        data={"api_key": api_key, "tag": tag, f"{php_alias}_id": identifier},
    )
    already_tagged = (
        php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        and "already tagged" in php_response.json()["error"]["message"]
    )
    if not already_tagged:
        # undo the tag, because we don't want to persist this change to the taskbase
        # Sometimes a change is already committed to the taskbase even if an error occurs.
        await php_api.post(
            f"/{php_alias}/untag",
            data={"api_key": api_key, "tag": tag, f"{php_alias}_id": identifier},
        )
    if (
        php_response.status_code != HTTPStatus.OK
        and php_response.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")

    entity_plural = f"{entity}s"
    py_response = await py_api.post(
        f"/{entity_plural}/tag?api_key={api_key}",
        json={f"{php_alias}_id": identifier, "tag": tag},
    )

    # RFC 9457: Tag conflict now returns 409 instead of 500
    if php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR and already_tagged:
        assert py_response.status_code == HTTPStatus.CONFLICT
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
        assert re.match(
            pattern=rf"{entity.capitalize()} \d+ already tagged with " + f"'{tag}'.",
            string=py_response.json()["detail"],
        )
        return

    if py_response.status_code == HTTPStatus.NOT_FOUND:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
        py_error = py_response.json()
        php_error = php_response.json()["error"]
        assert py_error["code"] == php_error["code"]
        assert php_error["message"] == "Entity not found."
        assert re.match(rf"{entity.capitalize()} \d+ not found.", py_error["detail"])
        return

    assert py_response.status_code == php_response.status_code, php_response.json()
    if py_response.status_code != HTTPStatus.OK:
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert py_response.json()["detail"] == php_response.json()["error"]["message"]
        return

    php_json = php_response.json()
    py_json = py_response.json()
    py_json = nested_remove_single_element_list(py_json)
    assert py_json == php_json
