"""Utility functions for logging."""

import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from loguru import logger
from starlette.requests import Request
from starlette.responses import Response

from config import load_configuration


def setup_log_sinks(configuration_file: Path | None = None) -> None:
    """Configure loguru based on app configuration."""
    configuration = load_configuration(configuration_file)
    for nickname, sink_configuration in configuration.get("logging", {}).items():
        logger.info("Configuring sink", nickname=nickname, **sink_configuration)
        sink = sink_configuration.pop("sink")
        if sink == "sys.stderr":
            sink = sys.stderr
        # Logs the additionally provided data as JSON.
        sink_configuration.setdefault("serialize", True)
        # Decouples log calls from I/O and makes it multiprocessing safe.
        sink_configuration.setdefault("enqueue", True)
        logger.add(sink, **sink_configuration)


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
