# server
Python-based server prototype

## Development Roadmap
First we will mimic current server functionality, relying on many implementation details
present in the current production server:

 - Implement all GET endpoints using the SQL text queries based on PHP implementation,
   which should give near-identical responses to the current JSON endpoints. Minor
   exceptions are permitted but will be documented.
 - Implement non-GET endpoints in similar fashion.

At the same time we may also provide a work-in-progress "new" endpoint, but there won't
be official support for it at this stage. After we verify the output of the endpoints
are identical (minus any intentional documented differences), we will officially release
the new API. The old API will remain available. After that, we can start working on a
new version of the JSON API which is more standardized, leverages typing, and so on:

 - Clean up the database: standardize value formats where possible (e.g., (un)quoting
   contributor names in the dataset's contributor field), and add database level
   constraints on new values.
 - Redesign what the new API responses should look like and implement them,
   API will be available to the public as it is developed.
 - Refactor code-base to use ORM (using `SQLAlchemy`, `SQLModel`, or similar).
 - Officially release the modernized API.

There is no planned sunset date for the old API. This will depend on the progress with
the new API as well as the usage numbers of the old API.

## Change Notes
The first iteration of the new server has nearly identical responses to the old JSON
endpoints, but there are exceptions:

 - Providing input of invalid types (e.g., a non-integer dataset id).

   HTTP Header:
   ```diff
   - 412 Precondition Failed
   + 422 Unprocessable Entity
   ```

   JSON Content
   ```diff
   - {"error":{"code":"100","message":"Function not valid"}}
   + {"detail":[{"loc":["query","_dataset_id"],"msg":"value is not a valid integer","type":"type_error.integer"}]}
   ```

 - For any other error messages, the response is identical except that outer field
   will be `"detail"` instead of `"error"`:
   ```diff
   - {"error":{"code":"112","message":"No access granted"}}
   + {"detail":{"code":"112","message":"No access granted"}}
   ```

 - Dataset format names are normalized to be all lower-case
   (`"Sparse_ARFF"` ->  `"sparse_arff"`).
 - Non-`arff` datasets will not incorrectly have a `"parquet_ur"`:
   https://github.com/openml/OpenML/issues/1189
 - If `"creator"` contains multiple comma-separated creators it is always returned
   as a list, instead of it depending on the quotation used by the original uploader.
 - For (some?) datasets that have multiple values in `"ignore_attribute"`, this field
   is correctly populated instead of omitted.
