from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

import pyarrow as pa
import pyarrow.parquet as pq

from schemas.datasets.openml import FeatureType


def map_arrow_type(arrow_type: pa.DataType) -> FeatureType:
    """Map a PyArrow DataType to an OpenML FeatureType."""
    if pa.types.is_floating(arrow_type) or pa.types.is_integer(arrow_type) or pa.types.is_decimal(
        arrow_type
    ):
        return FeatureType.NUMERIC
    if pa.types.is_boolean(arrow_type) or pa.types.is_dictionary(arrow_type):
        return FeatureType.NOMINAL
    return FeatureType.STRING


@dataclass
class ColumnMeta:
    index: int
    name: str
    data_type: FeatureType
    number_of_missing_values: int


@dataclass
class ParquetMeta:
    num_rows: int
    num_columns: int
    md5_checksum: str
    columns: list[ColumnMeta] = field(default_factory=list)


def read_parquet_metadata(file_bytes: bytes) -> ParquetMeta:
    """Parse *file_bytes* as Parquet and extract schema / quality metadata.

    Raises ``ValueError`` if the bytes are not a valid Parquet file.
    """
    try:
        buf = io.BytesIO(file_bytes)
        pf = pq.ParquetFile(buf)
    except Exception as exc:
        msg = "File is not a valid Parquet file."
        raise ValueError(msg) from exc

    schema = pf.schema_arrow
    num_rows = pf.metadata.num_rows
    md5 = hashlib.md5(file_bytes, usedforsecurity=False).hexdigest()  # noqa: S324

    # Read full table once to count per-column nulls
    table = pf.read()

    columns: list[ColumnMeta] = []
    for idx, col_name in enumerate(schema.names):
        col = table.column(col_name)
        null_count = col.null_count
        columns.append(
            ColumnMeta(
                index=idx,
                name=col_name,
                data_type=map_arrow_type(schema.field(col_name).type),
                number_of_missing_values=null_count,
            )
        )

    return ParquetMeta(
        num_rows=num_rows,
        num_columns=len(columns),
        md5_checksum=md5,
        columns=columns,
    )
