import os
from pathlib import Path

from config import _apply_defaults_to_siblings, load_database_configuration


def test_apply_defaults_to_siblings_applies_defaults() -> None:
    input_ = {"defaults": {1: 1}, "other": {}}
    expected = {"other": {1: 1}}
    output = _apply_defaults_to_siblings(input_)
    assert expected == output


def test_apply_defaults_to_siblings_does_not_override() -> None:
    input_ = {"defaults": {1: 1}, "other": {1: 2}}
    expected = {"other": {1: 2}}
    output = _apply_defaults_to_siblings(input_)
    assert expected == output


def test_apply_defaults_to_siblings_ignores_nontables() -> None:
    input_ = {"defaults": {1: 1}, "other": {1: 2}, "not-a-table": 3}
    expected = {"other": {1: 2}, "not-a-table": 3}
    output = _apply_defaults_to_siblings(input_)
    assert expected == output


def test_load_configuration_adds_environment_variables(default_configuration_file: Path) -> None:
    database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"]["username"] == "root"

    load_database_configuration.cache_clear()
    os.environ["OPENML_DATABASES_OPENML_USERNAME"] = "foo"
    database_configuration = load_database_configuration(default_configuration_file)
    assert database_configuration["openml"]["username"] == "foo"
