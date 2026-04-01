"""Utility functions for logging."""

from loguru import logger

from config import load_configuration


def setup_log_sinks() -> None:
    """Configure loguru based on app configuration."""
    configuration = load_configuration()
    for nickname, sink_configuration in configuration.get("logging", {}).items():
        logger.info("Configuring sink", nickname=nickname, **sink_configuration)
        sink = sink_configuration.pop("sink")
        logger.add(sink, serialize=True, **sink_configuration)
