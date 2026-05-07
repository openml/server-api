"""Configuration logic and schema definitions.

The `get_config` function provides access to the most recently loaded configuration.
A default configuration is loaded if none is explicitly set.

Use `set_config` to use a different configuration.
To parse a configuration from a file and environment variables, use `parse_configuration`.
Example of loading a configuration with a custom TOML and .env file:

```
config = parse_config(
    dotenv_file=Path("path/to/.env"),
    configuration_file=Path("path/to/config.toml")
)
set_config(config)
```
and then consequent calls to `get_config` will return that configuration.
"""

import functools
import os
import tomllib
import typing
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv
from loguru import logger
from pydantic import AnyUrl, BaseModel, Field

TomlTable = dict[str, typing.Any]

CONFIG_DIRECTORY_ENV = "OPENML_REST_API_CONFIG_DIRECTORY"
CONFIG_FILE_ENV = "OPENML_REST_API_CONFIG_FILE"
DOTENV_FILE_ENV = "OPENML_REST_API_DOTENV_FILE"


_config: Configuration | None = None


@functools.cache
def get_config() -> Configuration:
    if _config is None:
        config = parse_config()
        set_config(config)
    return cast("Configuration", _config)


def set_config(configuration: Configuration) -> None:
    global _config  # noqa: PLW0603
    _config = configuration


class Configuration(BaseModel, frozen=True):
    openml_database: DatabaseConfiguration
    expdb_database: DatabaseConfiguration
    development: DevelopmentConfiguration
    routing: RoutingConfiguration
    logging: list[LoggingConfiguration]


class DatabaseConfiguration(BaseModel, frozen=True):
    """Settings for one database connection."""

    host: str = Field(default="database", description="Database server host name")
    port: int = Field(default=3306, gt=0)
    database: str = Field(description="Database name")
    username: str = Field(default="root")
    password: str = Field(default="ok")
    echo: bool = Field(
        default=False,
        description="https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine.params.echo",
    )
    drivername: str = Field(
        default="mysql+aiomysql",
        description="SQLAlchemy `dialect` and `driver`: https://docs.sqlalchemy.org/en/20/dialects/index.html",
    )


class DevelopmentConfiguration(BaseModel, frozen=True):
    """Settings for development or test specific features."""

    allow_test_api_keys: bool = Field(default=False)


class RoutingConfiguration(BaseModel, frozen=True):
    root_path: str = Field(default="", description="Path prefix under which the service is hosted.")
    minio_url: AnyUrl = Field(description="URL to the MinIO server or service")
    server_url: AnyUrl = Field(
        description="URL to this server (excluding the path prefix of `fastapi.root_path`).",
    )


class LoggingConfiguration(BaseModel, frozen=True):
    """Configuration for a single log sink.

    You can add any arguments that `loguru.logger.add` allows,
    the `sink` will be used as first positional argument.
    See also: https://loguru.readthedocs.io/en/stable/api/logger.html
    """

    sink: str
    level: Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"]
    rotation: str | None = Field(
        default=None,
        description="Set rotation policy by date or file size.",
    )
    retention: str | None = Field(
        default=None,
        description="Timespan after which automatic cleanup occurs.",
    )
    compression: str | None = Field(default="gz")
    # Logs provided variables as JSON
    serialize: bool = Field(default=True)
    # Decouples log calls from I/O and makes it multiprocessing safe.
    enqueue: bool = Field(default=True)


def _load_database_configuration(
    configurations: dict[str, dict[str, str]],
) -> dict[str, DatabaseConfiguration]:
    database_configurations = {}
    for db_alias, db_configuration in configurations.items():
        credentials = {
            "username": os.environ.get(
                f"OPENML_DATABASES_{db_alias.upper()}_USERNAME",
                "root",
            ),
            "password": os.environ.get(
                f"OPENML_DATABASES_{db_alias.upper()}_PASSWORD",
                "ok",
            ),
        }
        database_configurations[db_alias] = DatabaseConfiguration(**db_configuration, **credentials)

    return database_configurations


def parse_config(
    dotenv_file: Path | None = None,
    configuration_file: Path | None = None,
) -> Configuration:
    """Load configuration from file and environment variables.

    The parsed configuration is returned but not used by default for other calls in this module.
    """
    _config_directory = Path(os.getenv(CONFIG_DIRECTORY_ENV, Path(__file__).parent))
    _config_directory = _config_directory.expanduser().absolute()
    logger.info(
        "Determined configuration directory to be {configuration_directory}.",
        configuration_directory=_config_directory,
    )

    if not dotenv_file:
        dotenv_filepath = os.getenv(DOTENV_FILE_ENV, _config_directory / ".env")
        dotenv_file = Path(dotenv_filepath).expanduser().absolute()

    logger.info(
        "Determined dotenv file path to be {dotenv_file}.",
        dotenv_file=dotenv_file,
    )
    load_dotenv(dotenv_file)

    if not configuration_file:
        config_filepath = os.getenv(CONFIG_FILE_ENV, _config_directory / "config.toml")
        configuration_file = Path(config_filepath).expanduser().absolute()

    logger.info(
        "Determined config file path to be {config_file}.",
        config_file=configuration_file,
    )

    config = tomllib.loads(configuration_file.read_text())
    db_configurations = _load_database_configuration(config["databases"])
    return Configuration(
        routing=RoutingConfiguration(**config["routing"]),
        logging=[
            LoggingConfiguration(**sink_configuration)
            for sink_configuration in config["logging"].values()
        ],
        openml_database=db_configurations["openml"],
        expdb_database=db_configurations["expdb"],
        development=DevelopmentConfiguration(**config["development"]),
    )
