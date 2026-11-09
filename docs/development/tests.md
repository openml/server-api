# Testing

This page covers running and writing tests for the REST API.
It assumes you already followed the instructions to set up your [Development Environment](setup.md).

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
```bash
docker compose exec python-api python -m pytest tests -m "not php_api and not slow"
```

Some tests require elastic search indices to be constructed.
These indices can be constructed by the PHP API container on startup,
but by default this is turned off because it can be a time consuming process.
If you see skipped tests indicating errors with elasticsearch, it is likely that
indices still need to be created. To do so, set the `INDEX_ES_DURING_STARTUP` variable
in the `docker/php/.env` file to `true` before starting the container.

## Writing Tests

We use [Pytest](https://docs.pytest.org) for writing and running tests.

### File Structure
When writing tests, we have the following additional conventions on the file structure:

 - Use a `_test` suffix when naming our files (not a `test_` prefix). Our tests already exist in a `tests` directory, and in common tree list side panels it's likely you can only see the start of file names, so this is more informative.
 - One dedicated test file per endpoint

The diagram below shows the structure of the `tests/` directory visually.
Omitted files are indicated with `...`.
```mermaid
treeView-beta
database/
  runs_test.py  ## Tests for src/database/runs.py
  ...
dependencies/  ## Tests for dependencies of src/routers/dependencies.py
  ...
resources/  ## Files required for testing purposes
  ...
routers/
  dataset_tag_test.py  ## tests for src/routers/datasets.py's `/datasets/{IDENTIFIER}/tag` endpoint
  ...
config_test.py  ## Tests for config.py
conftest.py  ## Pytest configuration and fixtures
constants.py  ## Constants used for multiple tests (e.g.,
users.py ##  Stubs and constants for user accounts
```

### General Test Guidelines
Some guidelines and things to keep in mind when writing tests:

 - Try to keep tests small, so that they fail for one particular reason only.
 - Mark tests that update the database in anyway with the `mut` marker (`@pytest.mark.mut`).
 - If the test is excessively slow (>0.1 sec) and does not connect to PHP, use a `slow` marker. Tests that include PHP always require roundtrips through other services which makes them slow by default. PHP tests can be filtered out with the automatically generated "php_api" marker.
 - When writing assertions the expected value (a constant, or a php response) should be on the right (`assert response == expected`).

### Fixtures
There are a number of fixtures in `conftest.py`, here is a quick rundown of the most notable ones:

    - `py_api` and `php_api`: an async client for the Python- and PHP-based REST APIs, respectively. The `py_api` client has its normal dependency injection for database connections patched to use the connection and session fixtures below.
    - `expdb_connection` and `userdb_connection`: an AsyncConnection to the "expdb" OpenML database. This fixture is function-scoped and automatically starts a transaction which is rolled back as long as no `commit` is made.
    - `expdb_session` and `userdb_session`: an AsyncSession that is bound to the respective connection. This means it also has automatic rollback. Any changes that need to be visible to the `py_api` fixture can be performed on this session (see below).

The pseudocode below shows how you might combine these for a test of the new REST API, either as standalone or when compared to the PHP API:

```python
async def test_python(py_api: httpx.AsyncClient, expdb_session: AsyncSession) -> None:
    await expdb_session.execute(
        text("INSERT INTO dataset ..."), params=...
    )  # Insert dataset with id 42

    response = await py_api.get(
        "/datasets/42"
    )  # Since this call shares the session, it should retrieve this data

    assert ...
    # after the test is done, the fixture clean up will ensure the change is not committed to the database, no extra code needed


async def test_python_and_php(
    py_api: httpx.AsyncClient, php_api: httpx.AsyncClient, expdb_connection: AsyncConnection
) -> None:
    await expdb_connection.execute(
        text("INSERT INTO dataset ..."), parameters=...
    )  # Insert dataset with id 42
    await expdb_connection.commit()  # We need to persist the data in the database, because the PHP REST API cannot see our transaction

    response = await php_api.get(
        "/datasets/42"
    )  # The PHP REST API can see the dataset, because it exists in the database
    response = await py_api.get("/datasets/42")  # The Python REST API can see the dataset also

    # We need to clean up after ourselves, otherwise the test has side effects.
    # This isn't a great pattern, prefer instead the use of context managers which will execute the delete statements even if unexpected exceptions occur.
    await expdb_connection.execute(text("DELETE FROM dataset ..."), parameters=...)
    await expdb_connection.commit()
```

???- "Why not always use the `*_connection`?"

    As this implementation will make more and more use of ORM models, it is more convenient to have access to an `AsyncSession` object which can deal with those models.
    Eventually, when verification against PHP REST API output is no longer necessary, we do not even need the `AsyncConnection` objects anymore at all.


Above fixtures have considerable per-test overhead. Use them only when you need them. More details in the next section.

### Writing Tests for an Endpoint
Because the `py_api` and database fixtures provide considerable per-test overhead,
follow these guidelines for writing a test suite for an endpoint.

!!! warning "Code snippets may not work"

    The code below is provided as a guide, but isn't automatically tested (yet). This means it may be out of sync.
    For examples that work, reference our test suite.

Include tests against `py_api` for input validation specific to that endpoint. Validation in reused components should be tested centrally (e.g., Pagination).
```python
def test_get_dataset_identifier_validation(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/not-an-integer")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

Include one test against the `py_api` that confirms a successful request has the expected result:

```python
def test_get_dataset_success(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/1")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {...}  # some expected data
```

For all other tests, do not use `py_api` but call the implementing function directly. For example, do not call `client.get("/datasets/1")` but instead `get_dataset`:

```python
async def test_get_dataset_private_success(
    expdb_session: AsyncSession, userdb_session: AsyncSession
) -> None:
    private_dataset = 42
    owner_of_that_dataset = OWNER_USER
    dataset = await get_dataset(
        dataset_id=42,
        user=owner_of_that_dataset,
        userdb_session=userdb_session,
        expdb_session=expdb_session,
    )
    assert dataset.id == private_dataset


async def test_get_dataset_private_access_denied(
    expdb_session: AsyncSession, userdb_session: AsyncSession
) -> None:
    private_dataset = 42
    owner_of_that_dataset = SOME_USER  # Test User defined in a common file
    with pytest.raises(DatasetNoAccessError) as e:
        await get_dataset(
            dataset_id=42,
            user=owner_of_that_dataset,
            userdb_session=userdb_session,
            expdb_session=expdb_session,
        )
    assert e.value.status_code == HTTPStatus.FORBIDDEN
```

*note:* We will likely mock the database layer at some point, but it's still taking shape.

For the initial development of this API, we want to have a clear mapping from PHP API output to the new output.
We also want to be aware of quirks that the PHP API might have.
For both these reasons, we write what we call "migration" tests: they call both APIs with a variety of input and compare the result.
Note that in some cases, there are some quite significant differences between the PHP and the Python based API.
That's okay, but in that case we want to "document" the behavior of both in the test.
Please reference a few implemented migration tests to get a better understanding, but here is a high level sketch:

```python
async def test_get_dataset(py_api: httpx.AsyncClient, php_api: httpx.AsyncClient) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/datasets/1"),
        php_api.get("/data/1"),
    )

    if py_response.status_code == HTTPStatus.OK and php_response.status_code == HTTPStatus.OK:
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

### Usage of the Database
You frequently need to write tests which include fetching from or writing to the database.
There is a test database that is prepopulated with data available for use as defined in our `compose.yaml` file.

The `expdb_connection`, `userdb_connection`, `expdb_session`, and `userdb_session` fixtures automatically start a transaction during setup and perform a rollback during teardown.
This means that as long as you do not `.commit()` any changes, the data will not persist.
This is a good thing. We do not want our tests to have side effects, as it might lead to inconsistent behavior.

There is one situation where you may need to commit to the database: migration tests.
Since the PHP API communicates to the database in a separate transaction, changes made within the transaction in "Python land" are not visible to PHP.
In this case, be extremely careful! You *must* write the test so that even if things fail unexpectedly, there is no data left behind.
Generally speaking, you want to use a context manager that cleans up after you. In some cases you may need to clean up after yourself during the test.
