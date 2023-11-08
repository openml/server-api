# Migration
This implementation currently maintains two separate endpoints.
There are "old" endpoints (Python-V1), which mimic responses of the PHP REST API (PHP-V1)
as closely as possible, and new endpoints (V2) which have some additional changes and
will be updated going forward.

The advised way to upgrade connector packages that currently interact with the old
JSON API is to first migrate from the old PHP API to our re-implemented V1 API.
See "[V1: PHP to Python](#v1--php-to-python)" for the differences between the PHP and
Python API. After that migration, continue with the "[V1 to V2](#v1-to-v2)" guide.

Connectors currently using the XML API are recommended to upgrade to V2 directly,
in which case using the generated REST API documentation is recommended.

## V1: PHP to Python

The first iteration of the new server has nearly identical responses to the old JSON
endpoints, but there are exceptions. Most exceptions either bug fixes, or arise from
technical limitations.

### All Endpoints
The following changes affect all endpoints.

#### Error on Invalid Input
When providing input of invalid types (e.g., a non-integer dataset id) the HTTP header
and JSON content will be different.

```diff title="HTTP Header"
- 412 Precondition Failed
+ 422 Unprocessable Entity
```

```diff title="JSON Content"
- {"error":{"code":"100","message":"Function not valid"}}
+ {"detail":[{"loc":["query","_dataset_id"],"msg":"value is not a valid integer","type":"type_error.integer"}]}
```

#### Other Errors
For any other error messages, the response is identical except that outer field will be `"detail"` instead of `"error"`:

```diff title="JSON Content"
- {"error":{"code":"112","message":"No access granted"}}
+ {"detail":{"code":"112","message":"No access granted"}}
```

In some cases the JSON endpoints previously returned XML ([example](https://github.com/openml/OpenML/issues/1200)).
Python-V1 will always return JSON.

```diff title="XML replaced by JSON"
- <oml:error xmlns:oml="http://openml.org/openml">
-   <oml:code>103</oml:code>
-   <oml:message>Authentication failed</oml:message>
- </oml:error>
+ {"detail": {"code":"103", "message": "Authentication failed" } }
```

### Datasets

#### `GET /{dataset_id}`
 - Dataset format names are normalized to be all lower-case
   (`"Sparse_ARFF"` ->  `"sparse_arff"`).
 - Non-`arff` datasets will not incorrectly have a `"parquet_url"`:
   https://github.com/openml/OpenML/issues/1189
 - If `"creator"` contains multiple comma-separated creators it is always returned
   as a list, instead of it depending on the quotation used by the original uploader.
 - For (some?) datasets that have multiple values in `"ignore_attribute"`, this field
   is correctly populated instead of omitted.


## V1 to V2
Most of the changes are focused on standardizing responses.

### Datasets

#### `GET /{dataset_id}`

 - Processing date is formatted with a `T` in the middle:
   ```diff title="processing_date"
   - "2019-07-09 15:22:03"
   + "2019-07-09T15:22:03"
   ```
 - Fields which may contain lists of values (e.g., `creator`, `contributor`) now always
   returns a list (which may also be empty or contain a single element).
 - Fields without a set value are no longer automatically removed from the response.
