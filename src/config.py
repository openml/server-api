import functools
import os
import tomllib
import typing
from pathlib import Path

from dotenv import load_dotenv

TomlTable = dict[str, typing.Any]

CONFIG_PATH = Path(__file__).parent / "config.toml"


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


def load_routing_configuration(file: Path = CONFIG_PATH) -> TomlTable:
    return typing.cast("TomlTable", _load_configuration(file)["routing"])


@functools.cache
def load_database_configuration(file: Path = CONFIG_PATH) -> TomlTable:
    configuration = _load_configuration(file)
    database_configuration = _apply_defaults_to_siblings(
        configuration["databases"],
    )
    load_dotenv()
    database_configuration["openml"]["username"] = os.environ.get(
        "OPENML_DATABASES_OPENML_USERNAME",
        "root",
    )
    database_configuration["openml"]["password"] = os.environ.get(
        "OPENML_DATABASES_OPENML_PASSWORD",
        "ok",
    )
    database_configuration["expdb"]["username"] = os.environ.get(
        "OPENML_DATABASES_EXPDB_USERNAME",
        "root",
    )
    database_configuration["expdb"]["password"] = os.environ.get(
        "OPENML_DATABASES_EXPDB_PASSWORD",
        "ok",
    )
    return database_configuration


def load_configuration(file: Path = Path(__file__).parent / "config.toml") -> TomlTable:
    return tomllib.loads(file.read_text())
