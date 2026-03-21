import logging

import pytest

from routers.openml.tasktype import parse_api_constraints


@pytest.mark.parametrize(
    ("api_constraints", "expected_data_type"),
    [
        # 1. Valid JSON string with data_type
        ('{"data_type": "matrix"}', "matrix"),
        # 2. Valid dict with data_type
        ({"data_type": "matrix"}, "matrix"),
        # 3. Malformed JSON string → None
        ("{bad json", None),
        # 4. Empty string → None
        ("", None),
        # 5. Valid JSON/dict without data_type → None
        ('{"other_key": "val"}', None),
        ({"other_key": "val"}, None),
        # 6. data_type present but empty string → None
        ('{"data_type": ""}', None),
        ({"data_type": ""}, None),
        # 7. Non-dict JSON (list) → None
        ('["array"]', None),
        # 8. None → None
        (None, None),
        # 9. Non-dict JSON (int) → None
        ("42", None),
        # 10. data_type is non-string (int) → None
        ('{"data_type": 123}', None),
        ({"data_type": 123}, None),
    ],
    ids=[
        "valid_json_string",
        "valid_dict",
        "malformed_json",
        "empty_string",
        "json_missing_data_type",
        "dict_missing_data_type",
        "json_empty_data_type",
        "dict_empty_data_type",
        "non_dict_json_list",
        "none_value",
        "non_dict_json_int",
        "json_non_string_data_type",
        "dict_non_string_data_type",
    ],
)
def test_parse_api_constraints(
    api_constraints: object,
    expected_data_type: str | None,
) -> None:
    result = parse_api_constraints(
        api_constraints,
        task_type_id=1,
        input_name="source_data",
    )
    assert result == expected_data_type


def test_parse_api_constraints_unsupported_type() -> None:
    """Unsupported types (e.g. int, list passed directly) should return None."""
    result = parse_api_constraints(
        12345,
        task_type_id=1,
        input_name="source_data",
    )
    assert result is None


class TestParseApiConstraintsLogging:
    """Verify correct log levels are emitted for different anomaly types."""

    def test_malformed_json_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            parse_api_constraints(
                "{bad json",
                task_type_id=1,
                input_name="source_data",
            )
        assert any("malformed_json" in r.message for r in caplog.records)

    def test_empty_string_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            parse_api_constraints(
                "",
                task_type_id=1,
                input_name="source_data",
            )
        assert any("empty_string" in r.message for r in caplog.records)

    def test_non_dict_json_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            parse_api_constraints(
                '["array"]',
                task_type_id=1,
                input_name="source_data",
            )
        assert any("non_dict_json" in r.message for r in caplog.records)

    def test_unsupported_type_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            parse_api_constraints(
                12345,
                task_type_id=1,
                input_name="source_data",
            )
        assert any("unsupported_type" in r.message for r in caplog.records)

    def test_missing_data_type_logs_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG):
            parse_api_constraints(
                '{"other_key": "val"}',
                task_type_id=1,
                input_name="source_data",
            )
        assert any("missing_data_type" in r.message for r in caplog.records)

    def test_valid_constraint_no_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG):
            result = parse_api_constraints(
                '{"data_type": "matrix"}',
                task_type_id=1,
                input_name="source_data",
            )
        assert result == "matrix"
        assert len(caplog.records) == 0
