from io import BytesIO, StringIO

import pyarrow as pa
import pyarrow.parquet as pq

from core.feature_analysis import analyze_arff, analyze_parquet
from schemas.datasets.openml import FeatureType


def test_analyze_arff_dense():
    arff_data = """@RELATION test
@ATTRIBUTE a NUMERIC
@ATTRIBUTE b {x,y}
@ATTRIBUTE c STRING
@DATA
1,x,hello
2,y,world
?,? ,?
"""
    features = analyze_arff(StringIO(arff_data))
    assert len(features) == 3

    assert features[0].name == "a"
    assert features[0].data_type == FeatureType.NUMERIC
    assert features[0].number_of_missing_values == 1
    assert features[0].nominal_values is None

    assert features[1].name == "b"
    assert features[1].data_type == FeatureType.NOMINAL
    assert features[1].nominal_values == ["x", "y"]
    assert features[1].number_of_missing_values == 1

    assert features[2].name == "c"
    assert features[2].data_type == FeatureType.STRING
    assert features[2].number_of_missing_values == 1


def test_analyze_arff_sparse():
    arff_data = """@RELATION test
@ATTRIBUTE a NUMERIC
@ATTRIBUTE b NUMERIC
@ATTRIBUTE c {X,Y}
@DATA
{0 1, 2 X}
{1 5}
{0 ?, 2 ?}
"""
    features = analyze_arff(StringIO(arff_data))
    assert len(features) == 3

    # index 0: 1, missing(0), ? -> 1 missing
    assert features[0].name == "a"
    assert features[0].number_of_missing_values == 1

    # index 1: missing(0), 5, missing(0) -> 0 missing
    assert features[1].name == "b"
    assert features[1].number_of_missing_values == 0

    # index 2: X, missing(None?), ?
    # Row 1: {1 5} -> index 2 is missing. In sparse ARFF, if it's missing it's the 0-th element for nominal.
    assert features[2].name == "c"
    assert features[2].number_of_missing_values == 1  # Only from row 2 {0 ?, 2 ?}


def test_analyze_arff_sparse_all_missing():
    arff_data = """@RELATION sparse
@ATTRIBUTE a NUMERIC
@DATA
{0 ?}
?
{}
"""
    # row 0: ? -> missing
    # row 1: ? -> missing
    # row 2: {} -> index 0 is missing from dict -> default (0) -> NOT missing
    features = analyze_arff(StringIO(arff_data))
    assert features[0].number_of_missing_values == 2


def test_analyze_arff_metadata():
    arff_data = """@RELATION test
@ATTRIBUTE a NUMERIC
@ATTRIBUTE b NUMERIC
@ATTRIBUTE c NUMERIC
@DATA
1,2,3
"""
    features = analyze_arff(
        StringIO(arff_data), target_features=["c"], ignore_features=["b"], row_id_features=["a"]
    )
    assert features[0].is_row_identifier is True
    assert features[1].is_ignore is True
    assert features[2].is_target is True
    assert features[0].is_target is False


def test_analyze_parquet():
    data = [
        pa.array([1, 2, None]),
        pa.array(["cat", "dog", "cat"]),
        pa.array([True, False, None]),
        pa.array(["v1", "v2", "v3"], type=pa.dictionary(pa.int8(), pa.string())),
    ]
    schema = pa.schema(
        [
            ("f1", pa.int64()),
            ("f2", pa.string()),
            ("f3", pa.bool_()),
            ("f4", pa.dictionary(pa.int8(), pa.string())),
        ]
    )
    table = pa.Table.from_arrays(data, schema=schema)

    buf = BytesIO()
    pq.write_table(table, buf)
    buf.seek(0)

    features = analyze_parquet(buf, target_features=["f3"])

    assert len(features) == 4

    assert features[0].name == "f1"
    assert features[0].data_type == FeatureType.NUMERIC
    assert features[0].number_of_missing_values == 1

    assert features[1].name == "f2"
    assert features[1].data_type == FeatureType.NOMINAL
    assert sorted(features[1].nominal_values) == ["cat", "dog"]

    assert features[2].name == "f3"
    assert features[2].data_type == FeatureType.NOMINAL
    assert features[2].is_target is True
    assert features[2].number_of_missing_values == 1
    assert features[2].nominal_values == ["false", "true"]

    assert features[3].name == "f4"
    assert features[3].data_type == FeatureType.NOMINAL
    assert sorted(features[3].nominal_values) == ["v1", "v2", "v3"]
