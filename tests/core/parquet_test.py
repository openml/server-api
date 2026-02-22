from __future__ import annotations

import io

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from core.parquet import FeatureType, ParquetMeta, map_arrow_type, read_parquet_metadata

_NUM_TEST_ROWS = 3
_NUM_TEST_COLS = 3
_EXPECTED_MISSING = 2


def _make_parquet_bytes(**columns: pa.Array) -> bytes:
    """Build an in-memory Parquet file from keyword-arg columns."""
    table = pa.table(columns)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("arrow_type", "expected"),
    [
        (pa.int32(), FeatureType.NUMERIC),
        (pa.int64(), FeatureType.NUMERIC),
        (pa.float32(), FeatureType.NUMERIC),
        (pa.float64(), FeatureType.NUMERIC),
        (pa.bool_(), FeatureType.NOMINAL),
        (pa.dictionary(pa.int8(), pa.utf8()), FeatureType.NOMINAL),
        (pa.string(), FeatureType.STRING),
        (pa.utf8(), FeatureType.STRING),
        (pa.date32(), FeatureType.STRING),
        (pa.timestamp("ms"), FeatureType.STRING),
    ],
)
def test_map_arrow_type(arrow_type: pa.DataType, expected: FeatureType) -> None:
    assert map_arrow_type(arrow_type) == expected


def test_read_parquet_metadata_returns_correct_shape() -> None:
    data = _make_parquet_bytes(
        a=pa.array([1, 2, 3], type=pa.int32()),
        b=pa.array([1.0, 2.0, 3.0], type=pa.float64()),
        label=pa.array(["x", "y", "z"], type=pa.string()),
    )
    meta: ParquetMeta = read_parquet_metadata(data)

    assert meta.num_rows == _NUM_TEST_ROWS
    assert meta.num_columns == _NUM_TEST_COLS
    assert len(meta.columns) == _NUM_TEST_COLS
    assert meta.md5_checksum  # non-empty


def test_read_parquet_metadata_column_types() -> None:
    data = _make_parquet_bytes(
        numeric=pa.array([1, 2], type=pa.int64()),
        text=pa.array(["a", "b"], type=pa.string()),
    )
    meta = read_parquet_metadata(data)

    col_map = {c.name: c.data_type for c in meta.columns}
    assert col_map["numeric"] == FeatureType.NUMERIC
    assert col_map["text"] == FeatureType.STRING


def test_read_parquet_metadata_counts_missing_values() -> None:
    data = _make_parquet_bytes(
        col=pa.array([1, None, 3, None], type=pa.int32()),
    )
    meta = read_parquet_metadata(data)
    assert meta.columns[0].number_of_missing_values == _EXPECTED_MISSING


def test_read_parquet_metadata_zero_missing_values() -> None:
    data = _make_parquet_bytes(col=pa.array([1, 2, 3], type=pa.int32()))
    meta = read_parquet_metadata(data)
    assert meta.columns[0].number_of_missing_values == 0


def test_read_parquet_metadata_raises_on_invalid_bytes() -> None:
    with pytest.raises(ValueError, match="valid Parquet"):
        read_parquet_metadata(b"this is not parquet data at all!")


def test_read_parquet_metadata_md5_is_deterministic() -> None:
    data = _make_parquet_bytes(x=pa.array([1, 2, 3]))
    assert read_parquet_metadata(data).md5_checksum == read_parquet_metadata(data).md5_checksum
