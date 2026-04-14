# Testing

This page covers running and writing tests for the REST API.
It assumes you already followed the instructions on the ["Setup"](setup.md) page.

!!! note "Follow the documentation"

    Some tests and files in the current test suite need to be updated to reflect these conventions.
    This documentation specifies the desired way of doing things even if the source code does something else.

## Running Tests

Following the setup page, you can run tests when the services are running.
Start the services using one of two commands:

```bash
docker compose --profile apis up -d  # if you run tests which need PHP REST API
docker compose up python-api -d  # if you do not run tests that require the PHP API
```
and then invoke pytest:
```bash
docker compose exec python-api python -m pytest tests
```
As of writing, the full test suite ran in sequence takes about 2 minutes.
We generally recommend running subsets of the tests during development.
In particular, running only the tests which do not use fuzzing or the PHP API takes under 3 seconds:
```
docker compose exec python-api python -m pytest tests -m "not php_api and not slow"
```

## Writing Tests

We use the ubiquitous [Pytest](https://docs.pytest.org) framework when writing tests.

### File Structure
When writing tests, we have the following additional conventions on the file structure:

 - Use a `_test` suffix when naming our files (not a `test_` prefix). Our tests already exist in a `tests` directory, and in common tree list side panels it's likely you can only see the start of file names, so this is more informative.
 - One dedicated test file per endpoint


### General Test Guidelines
Some guidelines and things to keep in mind when writing tests:

 - Try to keep tests small, so that they fail for one particular reason only.
 - Mark tests that update the database in anyway with the `mut` marker (`@pytest.mark.mut`).
 - If the test is excessively slow (>0.1 sec) and does not connect to PHP, use a `slow` marker. Tests always require roundtrips through other services which makes them slow by default. These tests can be filtered out with the automatically generated "php_api" marker.
 - Four common fixtures you might need when writing tests are:
    - py_api: an async client for the Python based REST API
    - php_api: an async client for the PHP based REST API
    - expdb_test: an AsyncConnection to the "expdb" OpenML database.
    - user_test: an AsyncConnection to the "openml" OpenML database.
 - Above fixtures have considerable per-test overhead. Use them only when you need them.
 - When writing assertions the expected value (a constant, or a php response) should be on the right (`assert response == expected`).

### Writing Tests for an Endpoint
Because the `py_api` and database fixtures provide considerable per-test overhead,
follow these guidelines for writing a test suite for an endpoint.

Include tests against `py_api` for input validation specific to that endpoint. Validation in reused components should be tested centrally (e.g., Pagination).
```python
def test_get_dataset_identifier_validation(py_api: httpx.AsyncClient) -> None:
    response = py_api.get("/datasets/not-an-integer")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

Include one test against the `py_api` that confirms a successful request has the expected result:

```python
def test_get_dataset_success(py_api: httpx.AsyncClient) -> None:
    response = py_api.get("/datasets/1")
    assert response.status_code == HTTPStatus.SUCCESS
    assert response.json() == {...}  # some expected data
```

For all other tests, do not use `py_api` but call the implementing function directly. For example, do not call `client.get("/datasets/1")` but instead `get_dataset`:

```python
async def test_get_dataset_private_success(expdb_test: AsyncConnection, user_test: AsyncConnection) -> None:
    private_dataset = 42
    owner_of_that_dataset = OWNER_USER
    dataset = await get_dataset(dataset_id=42, user=owner_of_that_dataset, user_db=user_test, expdb_db=expdb_test)
    assert dataset.id == private_dataset

async def test_get_dataset_private_access_denied(expdb_test: AsyncConnection, user_test: AsyncConnection) -> None:
    private_dataset = 42
    owner_of_that_dataset = OWNER_USER  # Test User defined in a common file
    with pytest.raises(DatasetNoAccessError) as e:
        await get_dataset(dataset_id=42, user=owner_of_that_dataset, user_db=user_test, expdb_db=expdb_test)
    assert e.value.status_code == HTTPStatus.FORBIDDEN
```

*note:* We will likely mock the database layer at some point, but it's still taking shape.

For the initial development of this API, we want to have a clear mapping from PHP API output to the new output.
We also want to be aware of quirks that the PHP API might have.
For both these reasons, we write what we call "migration" tests: they call both APIs with a variety of input and compare the result.
Note that in some cases, there are some quite significant differences between the PHP and the Python based API.
That's okay, but in that case we want to "document" the behavior of both in the test.
Please reference a few implemented migration tests to get a better understanding, but here is a high level sketch:

```
async def test_get_dataset(py_api: httpx.AsyncClient, php_api: httpx.AsyncClient) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/datasets/1"),
        php_api.get("/data/1"),
    )

    if py_response.status_code == HTTPStatus.SUCCESS and php_response.status_code == HTTPStatus.SUCCESS:
        _assert_success_response_equal(py_response.json(), php_response.json())
    else:
        _assert_error_response_equal(py_response, php_response)

def _assert_success_response_equal(py_json, php_json) -> None:
    # PHP API returns numbers as strings
    py_json = nested_num_to_str(py_json)

    # There might be more differences which need addressing
    # ...
    # and then finally we compare the results to ensure the remaining data is identical
    assert py_json == php_json

def _assert_error_response_equal(py_response, php_response) -> None:
    # There might be some translation of error codes
    if py_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    elif ...:
        ...
    else:
        assert py_response.status_code == php_response.status_code

    # Python follows RFC9457 while PHP has a custom system:
    assert py_response.json()["code"] == php_response.json()["error"]["code"]

```
