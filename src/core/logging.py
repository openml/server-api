"""Utility functions for logging."""

import sys
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
        logger.add(sink, serialize=True, **sink_configuration)


async def add_request_context_to_log(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add a unique request id to each log call."""
    identifier = uuid.uuid4().hex
    with logger.contextualize(request_id=identifier):
        return await call_next(request)


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
