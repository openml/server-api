from typing import IO, Iterable
import arff
import pyarrow.parquet as pq
import pyarrow as pa
from schemas.datasets.openml import Feature, FeatureType

def analyze_arff(
    arff_stream: IO[str],
    target_features: Iterable[str] | None = None,
    ignore_features: Iterable[str] | None = None,
    row_id_features: Iterable[str] | None = None,
) -> list[Feature]:
    """Analyze an ARFF file and return a list of Feature objects."""
    dataset = arff.load(arff_stream)
    attributes = dataset["attributes"]
    data = dataset["data"]

    target_features = set(target_features or [])
    ignore_features = set(ignore_features or [])
    row_id_features = set(row_id_features or [])

    features = []
    for i, (name, type_info) in enumerate(attributes):
        if isinstance(type_info, list):
            data_type = FeatureType.NOMINAL
            nominal_values = type_info
        elif type_info.upper() in ("NUMERIC", "REAL", "INTEGER"):
            data_type = FeatureType.NUMERIC
            nominal_values = None
        elif type_info.upper() == "STRING":
            data_type = FeatureType.STRING
            nominal_values = None
        else:
            # Fallback or handle other types if necessary
            data_type = FeatureType.STRING
            nominal_values = None

        # Count missing values
        missing_count = 0
        if data:
            for row in data:
                # In liac-arff, data can be a list of lists or a list of dictionaries (for sparse)
                if isinstance(row, dict):
                    # Sparse format: only present values are in the dict
                    if i not in row:
                        # In sparse ARFF, if an index is missing from the dict, 
                        # it means it has the default value, which is usually 0.
                        # sparse ARFF in liac-arff:
                        # {index: value, ...}
                        # If it's missing, it's 0. 
                        # Missing values are represented as None in the dict if explicitly present.
                        # OpenML's sparse ARFF uses {index value, ...} 
                        # and missing values are simply not there if they are 0, 
                        # but if they are really missing they should be there as '?' 
                        # which liac-arff converts to None.
                        pass
                    elif row[i] is None:
                        missing_count += 1
                elif row[i] is None:
                    missing_count += 1

        features.append(
            Feature(
                index=i,
                name=name,
                data_type=data_type,
                is_target=name in target_features,
                is_ignore=name in ignore_features,
                is_row_identifier=name in row_id_features,
                number_of_missing_values=missing_count,
                nominal_values=nominal_values,
            )
        )
    return features

def analyze_parquet(
    source: str | IO[bytes],
    target_features: Iterable[str] | None = None,
    ignore_features: Iterable[str] | None = None,
    row_id_features: Iterable[str] | None = None,
) -> list[Feature]:
    """Analyze a Parquet file and return a list of Feature objects."""
    table = pq.read_table(source)
    schema = table.schema
    
    target_features = set(target_features or [])
    ignore_features = set(ignore_features or [])
    row_id_features = set(row_id_features or [])

    features = []
    for i, field in enumerate(schema):
        name = field.name
        pa_type = field.type
        
        # Determine data_type and nominal_values
        nominal_values = None
        if pa.types.is_floating(pa_type) or pa.types.is_integer(pa_type):
            data_type = FeatureType.NUMERIC
        elif pa.types.is_dictionary(pa_type):
            data_type = FeatureType.NOMINAL
            # Extract nominal values from dictionary
            # We need to look at the data to get the dictionary values
            column_data = table.column(i)
            # A column can have multiple chunks
            unique_values = set()
            for chunk in column_data.chunks:
                dictionary = chunk.dictionary
                for val in dictionary:
                    unique_values.add(val.as_py())
            nominal_values = sorted(list(unique_values))
        elif pa.types.is_string(pa_type) or pa.types.is_boolean(pa_type):
            # For Parquet, strings might be nominal if they don't have a dictionary
            # We needed to "Extract unique values from the data" for nominals in non-ARFF
            # In OpenML, if it's used for classification, it's nominal.
            # If we don't know, we might have to guess or treat all strings as nominal if they have 
            # few unique values. 
            
            # For Parquet, let's assume if it's not numeric, it's nominal for now, 
            # as that's common in ML datasets, unless it's explicitly string.
            
            # If it's boolean, it's definitely nominal [False, True].
            if pa.types.is_boolean(pa_type):
                data_type = FeatureType.NOMINAL
                nominal_values = ["false", "true"]
            else:
                # For string, let's extract unique values and see.
                column_data = table.column(i)
                unique_values = set()
                # For efficiency, we might not want to scan everything if it's huge
                for chunk in column_data.chunks:
                    for val in chunk.unique():
                        v = val.as_py()
                        if v is not None:
                            unique_values.add(str(v))
                
                # OpenML usually has a threshold, but let's just call it nominal if it's string 
                data_type = FeatureType.NOMINAL
                nominal_values = sorted(list(unique_values))
        else:
            data_type = FeatureType.STRING
            nominal_values = None

        # Count missing values
        missing_count = table.column(i).null_count

        features.append(
            Feature(
                index=i,
                name=name,
                data_type=data_type,
                is_target=name in target_features,
                is_ignore=name in ignore_features,
                is_row_identifier=name in row_id_features,
                number_of_missing_values=missing_count,
                nominal_values=nominal_values,
            )
        )
    return features
