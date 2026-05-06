import os
from unittest import mock

from config import _load_database_configuration


def test_load_configuration_adds_environment_variables() -> None:
    _db_alias = "openml"

    _fake_config = {
        _db_alias: {"database": "openml"},
    }
    database_configuration = _load_database_configuration(_fake_config)
    assert database_configuration[_db_alias].username == "root"

    _env_var_name = f"OPENML_DATABASES_{_db_alias.upper()}_USERNAME"
    with mock.patch.dict(os.environ, {_env_var_name: "foo"}):
        database_configuration = _load_database_configuration(_fake_config)
    assert database_configuration[_db_alias].username == "foo"
