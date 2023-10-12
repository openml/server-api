from __future__ import annotations

import tomllib
import typing
from pathlib import Path

TomlTable = dict[str, typing.Any]


def apply_defaults_to_subtables(configuration: TomlTable, table: str) -> TomlTable:
    defaults = configuration[table]["defaults"]
    return {
        subtable: defaults | overrides
        for subtable, overrides in configuration[table].items()
        if subtable != "defaults"
    }


def load_configuration(file: Path) -> TomlTable:
    configuration = tomllib.loads(file.read_text())
    configuration["databases"] = apply_defaults_to_subtables(
        configuration,
        table="databases",
    )
    return configuration


_configuration = load_configuration(Path(__file__).parent / "config.toml")
DATABASE_CONFIGURATION = _configuration["databases"]
