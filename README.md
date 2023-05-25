# server
Python-based server



## Change Notes
The first iteration of the new server has nearly identical responses to the old JSON endpoints.
There are however a few exceptions:

 - Providing input of invalid types (e.g., a non-integer dataset id).

   Old HTTP Header: `412 Precondition Failed`

   Old JSON Content:
   ```json
   {"error":{"code":"100","message":"Function not valid"}}
   ```

   New HTTP Header: `422 Unprocessable Entity`

   New JSON Content:
    ```json
   {"detail":[{"loc":["query","_dataset_id"],"msg":"value is not a valid integer","type":"type_error.integer"}]}
    ```
