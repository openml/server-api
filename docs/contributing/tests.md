# Writing Tests

This guide specifies the required testing strategy for the OpenML server API.
All tests MUST follow this strategy to ensure correctness while maintaining fast test execution.

## Testing Strategy Overview

Write tests at FOUR levels. Each level serves a specific purpose:

| Level | Purpose | Overhead |
|-------|---------|----------|
| Migration | Verify Python API matches PHP API | ~300ms |
| Integration | Test full FastAPI stack | ~60ms |
| Database | Test DB functions directly | ~4ms |
| Unit | Test input/output processing | ~1ms |

## 1. Migration Tests

You MUST write migration tests for every endpoint to verify correctness during PHP to Python migration.

**When to write these:** Test each endpoint against the PHP API to verify equivalent behavior.

**Key requirement:** Use `persisted_flow` (or similar) fixture to persist data to the database before the test, so the PHP API can also access it. Without persistence, the PHP API cannot see the test data.

### Example

```python
@pytest.mark.mut
async def test_flow_exists(
    persisted_flow: Flow,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    path = f"exists/{persisted_flow.name}/{persisted_flow.external_version}"
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/flows/{path}"),
        php_api.get(f"/flow/{path}"),
    )

    assert py_response.status_code == php_response.status_code
    assert py_response.json() == {"flow_id": persisted_flow.id}
```

### Persisting Data for PHP API Tests

When testing against the PHP API, you MUST persist data to the database because:
- The PHP API reads from the same database as Python
- The `expdb_test` fixture rolls back changes after each test by default
- Without persistence, PHP API will not see the test data

Use `persist=True` in `temporary_records` or use `persisted_*` fixtures:

```python
# Option 1: Use persisted fixture (recommended)
@pytest.fixture
async def persisted_flow(flow: Flow, expdb_test: AsyncConnection) -> AsyncIterator[Flow]:
    await expdb_test.commit()  # Persist to database
    yield flow
    await expdb_test.rollback()  # Rollback after test
    # Cleanup...

# Option 2: Use persist parameter
async with temporary_records(connection, insert_queries, delete_queries, persist=True):
    # Data is visible to both APIs
    pass
```

## 2. Integration Tests

You SHOULD write integration tests for critical paths that exercise the full FastAPI stack.

**When to write these:** Test expected paths that require the complete application stack (client, dependency injection, database). Limit to ONE test per kind of expected response.

**Important:** Creating the FastAPI TestClient has significant overhead (~60ms per test). Therefore, you MUST limit integration tests to critical paths only. Use database or unit tests for additional coverage.

### Example

```python
async def test_flow_exists(flow: Flow, py_api: httpx.AsyncClient) -> None:
    """Test flow exists - found case."""
    response = await py_api.get(f"/flows/exists/{flow.name}/{flow.external_version}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"flow_id": flow.id}


async def test_flow_exists_not_exists(py_api: httpx.AsyncClient) -> None:
    """Test flow exists - not found case."""
    response = await py_api.get("/flows/exists/foo/bar")
    assert response.status_code == HTTPStatus.NOT_FOUND
```

## 3. Database Tests

You SHOULD write database tests to verify database query behavior directly.

**When to write these:** Test database queries, ORM functions, and data retrieval logic.

**Advantage:** Fast execution (~4ms per test), no FastAPI overhead.

### Example

```python
async def test_database_flow_exists(flow: Flow, expdb_test: AsyncConnection) -> None:
    retrieved_flow = await database.flows.get_by_name(flow.name, flow.external_version, expdb_test)
    assert retrieved_flow is not None
    assert retrieved_flow.id == flow.id


async def test_database_flow_not_found(expdb_test: AsyncConnection) -> None:
    retrieved_flow = await database.flows.get_by_name("foo", "bar", expdb_test)
    assert retrieved_flow is None
```

### Database Fixtures and Rollback

The `expdb_test` and `user_test` fixtures use automatic rollback:

```python
@contextlib.asynccontextmanager
async def automatic_rollback(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        if transaction.is_active:
            await transaction.rollback()
```

**Behavior:**
- Default: Changes are rolled back after each test (safe, no cleanup needed)
- Use `persist=True` or `persisted_*` fixtures ONLY when data must be visible to external systems (e.g., PHP API)

## 4. Unit Tests

You SHOULD write unit tests to verify input/output processing and error handling.

**When to write these:** Test edge cases, error handling, input validation, and output formatting. Use `pytest.mark.parametrize` to test multiple inputs efficiently.

**Advantage:** Fast execution (~1ms per test), no database or API overhead.

### Example

```python
async def test_flow_exists_calls_db_correctly(
    name: str,
    external_version: str,
    expdb_test: AsyncConnection,
    mocker: MockerFixture,
) -> None:
    mocked_db = mocker.patch("database.flows.get_by_name", new_callable=mocker.AsyncMock)
    await flow_exists(name, external_version, expdb_test)
    mocked_db.assert_called_once_with(
        name=name,
        external_version=external_version,
        expdb=mocker.ANY,
    )


async def test_flow_exists_handles_not_found(
    mocker: MockerFixture, expdb_test: AsyncConnection
) -> None:
    mocker.patch("database.flows.get_by_name", return_value=None)
    with pytest.raises(FlowNotFoundError) as error:
        await flow_exists("foo", "bar", expdb_test)
    assert error.value.status_code == HTTPStatus.NOT_FOUND
```

### When to Mock

| Use Case | Approach |
|----------|----------|
| Testing input/output processing | Mock the database call |
| Testing error handling | Mock return value to trigger error |
| Testing database behavior | Use database tests instead |

## Test Markers

Use pytest markers to control test execution:

- `@pytest.mark.mut` - Migration tests (run against both PHP and Python APIs)
- Default - Fast unit/database/integration tests (run locally and on CI)

```bash
# Run only fast tests locally
pytest -m "not mut"

# Run all tests including migration
pytest -m "mut"
```

## Fixtures Reference

| Fixture | Purpose | Rollback | Use When |
|---------|---------|----------|----------|
| `expdb_test` | DB connection to experiment db | Automatic | Testing DB queries |
| `user_test` | DB connection to user db | Automatic | Testing user data |
| `py_api` | FastAPI test client with DB | Automatic | Integration tests |
| `php_api` | PHP API client | N/A | Migration tests |
| `flow` | Creates temp flow in DB | Automatic | Unit/DB tests |
| `persisted_flow` | Persists flow for both APIs | Manual cleanup | Migration tests |

## Performance Data

Understanding fixture overhead helps you write efficient tests.

### Fixture Overhead (5000 iterations)

| Fixtures Used | Time (s) |
|---------------|----------|
| None | 1.78 |
| `expdb_test` | 3.45 |
| `user_test` | 3.22 |
| `py_api` | 298.48 |
| `expdb_test` + `user_test` | 4.44 |
| All three | 307.91 |

### Key Observations

- **Database fixtures** add ~2ms overhead each
- **FastAPI TestClient** adds ~60ms overhead (two orders of magnitude more than DB)
- Adding multiple database fixtures is not free
- Use `pytest.mark.parametrize` at the database/unit level for multiple inputs

### Guidelines

1. DO use database tests with `pytest.mark.parametrize` for multiple inputs
2. DO mock database calls in unit tests for speed
3. DO limit integration tests to one per expected response type
4. DO NOT use `py_api` fixture unless testing the full FastAPI stack
5. DO NOT create a new database fixture per input in parameterized tests
