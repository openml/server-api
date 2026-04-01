import argparse
import sys
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response

from config import load_configuration
from core.errors import ProblemDetailError, problem_detail_exception_handler
from core.logging import setup_log_sinks
from database.setup import close_databases
from routers.mldcat_ap.dataset import router as mldcat_ap_router
from routers.openml.datasets import router as datasets_router
from routers.openml.estimation_procedure import router as estimationprocedure_router
from routers.openml.evaluations import router as evaluationmeasures_router
from routers.openml.flows import router as flows_router
from routers.openml.qualities import router as qualities_router
from routers.openml.runs import router as run_router
from routers.openml.setups import router as setup_router
from routers.openml.study import router as study_router
from routers.openml.tasks import router as task_router
from routers.openml.tasktype import router as ttype_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Manage application lifespan - startup and shutdown events."""
    yield
    await close_databases()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    uvicorn_options = parser.add_argument_group(
        "uvicorn",
        "arguments forwarded to uvicorn",
    )
    _ = uvicorn_options.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload",
    )
    _ = uvicorn_options.add_argument(
        "--host",
        default="127.0.0.1",
        type=str,
        help="Bind socket to this host.",
    )
    _ = uvicorn_options.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Bind socket to this port. If 0, an available port will be picked.",
    )
    return parser.parse_args()


async def add_request_context_to_log(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    identifier = uuid.uuid4().hex
    host = request.client.host if request.client else "unknown host"
    with logger.contextualize(request_id=identifier, client_ip=host):
        return await call_next(request)


async def request_response_logger(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    logger.info(
        "request",
        url=request.url,
        headers=request.headers,
        cookies=request.cookies,
        path_params=request.path_params,
        query_params=request.query_params,
        body=await request.body(),
    )
    response: Response = await call_next(request)
    logger.info(
        "response",
        status_code=response.status_code,
        headers=response.headers,
        media_type=response.media_type,
    )
    return response


def create_api() -> FastAPI:
    # Default logging configuration so we have logs during setup
    setup_sink = logger.add(sys.stderr, serialize=True)
    setup_log_sinks()

    fastapi_kwargs = load_configuration()["fastapi"]
    logger.info("Creating FastAPI App", lifespan=lifespan, **fastapi_kwargs)
    app = FastAPI(**fastapi_kwargs, lifespan=lifespan)

    logger.info("Setting up middleware and exception handlers.")
    # Order matters! Each added middleware wraps the previous, creating a stack.
    # See also: https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
    app.middleware("http")(request_response_logger)
    app.middleware("http")(add_request_context_to_log)

    app.add_exception_handler(ProblemDetailError, problem_detail_exception_handler)  # type: ignore[arg-type]

    logger.info("Adding routers to app")
    app.include_router(datasets_router)
    app.include_router(qualities_router)
    app.include_router(mldcat_ap_router)
    app.include_router(ttype_router)
    app.include_router(evaluationmeasures_router)
    app.include_router(estimationprocedure_router)
    app.include_router(task_router)
    app.include_router(flows_router)
    app.include_router(study_router)
    app.include_router(setup_router)
    app.include_router(run_router)

    logger.info("App setup completed.")
    logger.remove(setup_sink)
    return app


def main() -> None:
    args = _parse_args()
    uvicorn.run(
        app="main:create_api",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
