"""Utility functions for logging."""

import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from loguru import logger

from config import LoggingConfiguration

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


def setup_log_sinks(*configurations: LoggingConfiguration) -> None:
    """Configure loguru based on app configuration."""
    for sink_configuration in configurations:
        conf = sink_configuration.model_dump()
        logger.info("Configuring sink", **conf)
        sink = conf.pop("sink")
        if sink == "sys.stderr":
            sink = sys.stderr
            # defaults may be provided for rotation and retention,
            # but they are not valid options for stderr logging.
            conf.pop("rotation", None)
            conf.pop("retention", None)
            conf.pop("compression", None)
        logger.add(sink, **conf)


async def add_request_context_to_log(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add a unique request id to each log call."""
    identifier = uuid.uuid4().hex
    with logger.contextualize(
        request_id=identifier,
        method=request.method,
        path=request.url.path,
    ):
        return await call_next(request)


async def log_request_duration(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log the process and wallclock time for each call.

    Reported times cannot be attributed solely to processing the request.
    As multiple requests can be handled concurrently in the same process,
    process time may be spent on other requests as well. The same goes for
    wallclock time, which is additionally influenced by e.g., context switches.
    """
    start_mono_ns = time.monotonic_ns()
    start_process_ns = time.process_time_ns()
    response: Response = await call_next(request)

    duration_mono_ns = time.monotonic_ns() - start_mono_ns
    duration_process_ns = time.process_time_ns() - start_process_ns
    logger.info(
        "Request took {mono_ms} ms wallclock time (process time {process_ms} ms)",
        mono_ms=int(duration_mono_ns / 1_000_000),
        process_ms=int(duration_process_ns / 1_000_000),
        wallclock_time_ns=duration_mono_ns,
        process_time_ns=duration_process_ns,
        status=response.status_code,
    )
    return response


async def request_response_logger(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log the incoming request and outgoing response."""
    logger.info(
        "request",
        url=request.url,
        headers=request.headers,
        cookies=request.cookies,
        path_params=request.path_params,
        query_params=request.query_params,
    )
    response: Response = await call_next(request)
    logger.info(
        "response",
        status_code=response.status_code,
        headers=response.headers,
        media_type=response.media_type,
    )
    return response
