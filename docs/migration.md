# Migration to V1
The first iteration of the new server has nearly identical responses to the old JSON
endpoints, but there are exceptions.

## All Endpoints
The following changes affect all endpoints.

### Error on Invalid Input
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

### Other Errors
For any other error messages, the response is identical except that outer field will be `"detail"` instead of `"error"`:

```diff title="JSON Content"
- {"error":{"code":"112","message":"No access granted"}}
+ {"detail":{"code":"112","message":"No access granted"}}
```

## Datasets

 - Dataset format names are normalized to be all lower-case
   (`"Sparse_ARFF"` ->  `"sparse_arff"`).
 - Non-`arff` datasets will not incorrectly have a `"parquet_ur"`:
   https://github.com/openml/OpenML/issues/1189
 - If `"creator"` contains multiple comma-separated creators it is always returned
   as a list, instead of it depending on the quotation used by the original uploader.
 - For (some?) datasets that have multiple values in `"ignore_attribute"`, this field
   is correctly populated instead of omitted.
