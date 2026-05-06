import functools
import os
import tomllib
import typing
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

TomlTable = dict[str, typing.Any]

CONFIG_DIRECTORY_ENV = "OPENML_REST_API_CONFIG_DIRECTORY"
CONFIG_FILE_ENV = "OPENML_REST_API_CONFIG_FILE"
DOTENV_FILE_ENV = "OPENML_REST_API_DOTENV_FILE"

OPENML_DB_USERNAME_ENV = "OPENML_DATABASES_OPENML_USERNAME"
OPENML_DB_PASSWORD_ENV = "OPENML_DATABASES_OPENML_PASSWORD"  # noqa: S105  # not a password
EXPDB_DB_USERNAME_ENV = "OPENML_DATABASES_EXPDB_USERNAME"
EXPDB_DB_PASSWORD_ENV = "OPENML_DATABASES_EXPDB_PASSWORD"  # noqa: S105  # not a password

_config_file: Path | None = None


def _apply_defaults_to_siblings(configuration: TomlTable) -> TomlTable:
    defaults = configuration["defaults"]
    return {
        subtable: (defaults | overrides) if isinstance(overrides, dict) else overrides
        for subtable, overrides in configuration.items()
        if subtable != "defaults"
    }


@functools.cache
def _load_configuration(file: Path) -> TomlTable:
    return tomllib.loads(file.read_text())


def load_routing_configuration(file: Path = _config_file) -> TomlTable:
    return typing.cast("TomlTable", load_configuration(configuration_file=file)["routing"])


@functools.cache
def load_database_configuration(file: Path = _config_file) -> TomlTable:
    configuration = load_configuration(configuration_file=file)
    database_configuration = _apply_defaults_to_siblings(
        configuration["databases"],
    )
    database_configuration["openml"]["username"] = os.environ.get(
        OPENML_DB_USERNAME_ENV,
        "root",
    )
    database_configuration["openml"]["password"] = os.environ.get(
        OPENML_DB_PASSWORD_ENV,
        "ok",
    )
    database_configuration["expdb"]["username"] = os.environ.get(
        EXPDB_DB_USERNAME_ENV,
        "root",
    )
    database_configuration["expdb"]["password"] = os.environ.get(
        EXPDB_DB_PASSWORD_ENV,
        "ok",
    )
    return database_configuration


def load_configuration(
    dotenv_file: Path | None = None, configuration_file: Path | None = None
) -> None:
    """Load configuration from file and environment variables."""
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

    global _config_file
    _config_file = configuration_file

    return tomllib.loads(configuration_file.read_text())
