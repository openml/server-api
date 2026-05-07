import os
from unittest import mock

from config import _db_env_credentials


def test__db_env_credentials() -> None:
    db_alias = "openml"
    credentials = _db_env_credentials(db_alias)
    assert credentials["username"] == "root"
    assert credentials["password"] == "ok"  # noqa: S105

    env_var_name = f"OPENML_DATABASES_{db_alias.upper()}_USERNAME"
    env_var_pass = f"OPENML_DATABASES_{db_alias.upper()}_PASSWORD"
    with mock.patch.dict(os.environ, {env_var_name: "foo", env_var_pass: "bar"}):
        credentials = _db_env_credentials(db_alias)

    assert credentials["username"] == "foo"
    assert credentials["password"] == "bar"  # noqa: S105
