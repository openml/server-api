"""Make sure database transactions are committed *before* the response is sent.

Since FastAPI 0.118 the exit code of a `yield` dependency runs after the response is sent,
unless the dependency is declared with `scope="function"`.
Without it, clients may get a success response for data that is not (yet) saved.
"""

import ast
from collections.abc import AsyncIterator, Callable, MutableMapping
from pathlib import Path
from types import TracebackType
from typing import Annotated, Any, Self

import httpx
import pytest
from fastapi import Depends, FastAPI

import routers.dependencies
from routers.dependencies import expdb_session, fetch_user, userdb_session

SESSION_DEPENDENCIES = (expdb_session, userdb_session, fetch_user)
SOURCE_DIRECTORY = Path(__file__).parents[2] / "src"


class _FakeTransaction:
    def __init__(self, events: list[str], *, fail_commit: bool) -> None:
        self._events = events
        self._fail_commit = fail_commit

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self._events.append("rollback")
            return
        if self._fail_commit:
            self._events.append("commit failed")
            msg = "commit failed"
            raise RuntimeError(msg)
        self._events.append("commit")


class _FakeSession:
    events: list[str]
    fail_commit: bool = False

    def __init__(self, _engine: object) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def begin(self) -> _FakeTransaction:
        return _FakeTransaction(self.events, fail_commit=self.fail_commit)


def _make_app(events: list[str]) -> FastAPI:
    app = FastAPI()

    @app.post("/write")
    async def write(
        _session: Annotated[object, Depends(expdb_session, scope="function")],
    ) -> dict[str, str]:
        events.append("handler")
        return {"status": "ok"}

    @app.post("/fail")
    async def fail(
        _session: Annotated[object, Depends(expdb_session, scope="function")],
    ) -> None:
        msg = "boom"
        raise ValueError(msg)

    return app


def _record_response_start(
    app: FastAPI,
    events: list[str],
) -> Callable[..., Any]:
    async def spy(
        scope: MutableMapping[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        async def send_(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                events.append("response sent")
            await send(message)

        await app(scope, receive, send_)

    return spy


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    recorded: list[str] = []
    _FakeSession.events = recorded
    _FakeSession.fail_commit = False
    monkeypatch.setattr(routers.dependencies, "AsyncSession", _FakeSession)
    monkeypatch.setattr(routers.dependencies, "expdb_database", object)
    return recorded


@pytest.fixture
async def client(events: list[str]) -> AsyncIterator[httpx.AsyncClient]:
    app = _make_app(events)
    transport = httpx.ASGITransport(
        app=_record_response_start(app, events),
        raise_app_exceptions=False,
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_commit_happens_before_response(
    client: httpx.AsyncClient,
    events: list[str],
) -> None:
    response = await client.post("/write")
    assert response.status_code == httpx.codes.OK
    assert events == ["handler", "commit", "response sent"]


async def test_failing_commit_is_not_reported_as_success(
    client: httpx.AsyncClient,
    events: list[str],
) -> None:
    _FakeSession.fail_commit = True
    response = await client.post("/write")
    assert response.status_code == httpx.codes.INTERNAL_SERVER_ERROR
    assert "commit failed" in events


async def test_error_rolls_back(client: httpx.AsyncClient, events: list[str]) -> None:
    response = await client.post("/fail")
    assert response.status_code == httpx.codes.INTERNAL_SERVER_ERROR
    assert "rollback" in events
    assert "commit" not in events


def test_session_dependencies_are_function_scoped() -> None:
    """Every `Depends` on a session (or user) dependency must have `scope="function"`.

    Use e.g. `Depends(expdb_session, scope="function")`, otherwise the transaction
    is committed after the response is sent.
    """
    names = {dependency.__name__ for dependency in SESSION_DEPENDENCIES}
    offenders = []
    for path in SOURCE_DIRECTORY.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Depends"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in names
            ):
                continue
            scope = next((kw.value for kw in node.keywords if kw.arg == "scope"), None)
            if not (isinstance(scope, ast.Constant) and scope.value == "function"):
                offenders.append(f"{path.relative_to(SOURCE_DIRECTORY)}:{node.lineno}")
    assert not offenders
