import argparse
import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from loguru import logger

from config import load_configuration
from core.errors import ProblemDetailError, problem_detail_exception_handler
from core.logging import (
    add_request_context_to_log,
    log_request_duration,
    request_response_logger,
    setup_log_sinks,
)
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
async def lifespan(
    app: FastAPI | None,  # noqa: ARG001 # parameter required by FastAPI/Starlette
) -> AsyncIterator[None]:
    """Manage application lifespan - startup and shutdown events."""
    yield
    asyncio.gather(
        logger.complete(),
        close_databases(),
    )


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


def create_api(configuration_file: Path | None = None) -> FastAPI:
    # Default logging configuration so we have logs during setup
    logger.remove()
    setup_sink = logger.add(sys.stderr, serialize=True)
    setup_log_sinks(configuration_file)

    fastapi_kwargs = load_configuration(configuration_file)["fastapi"]
    logger.info("Creating FastAPI App", lifespan=lifespan, **fastapi_kwargs)
    app = FastAPI(**fastapi_kwargs, lifespan=lifespan)

    logger.info("Setting up middleware and exception handlers.")
    # Order matters! Each added middleware wraps the previous, creating a stack.
    # See also: https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
    app.middleware("http")(request_response_logger)
    app.middleware("http")(log_request_duration)
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
