# Writing Tests

This page documents the current testing strategy in this repository.
It is intentionally descriptive: it explains which test layers exist today and when each layer is used.

## Quick summary

- Use the lightest test layer that verifies the behavior you are changing.
- `py_api` (`fastapi.testclient.TestClient`) is intentionally used for integration and migration checks.
- Direct database tests verify SQL/database behavior.
- Direct function tests verify application logic with minimal fixture overhead.
- Mocking is used selectively to keep tests fast, while still validating real database behavior in dedicated tests.

## Test infrastructure in this repository

The core fixtures are defined in `tests/conftest.py`:

- `expdb_test` and `user_test` provide transactional database connections.
- `py_api` creates a FastAPI `TestClient` and overrides dependencies to use those transactional connections.
- `php_api` provides an HTTP client to the legacy PHP API for migration comparisons.

The transactional fixtures use rollback semantics, so most tests can mutate data without persisting changes.

## Test categories

### 1) Migration tests

Migration tests compare Python API responses against the legacy PHP API for equivalent endpoints.
These tests live under `tests/routers/openml/migration/`.

Characteristics:

- Use both `py_api` and `php_api` fixtures.
- Compare response status and response body (with explicit normalization where old/new formats differ).
- Focus on compatibility guarantees during migration.

Typical examples include dataset, flow, task, study, and evaluation migration checks.

### 2) Integration tests (FastAPI TestClient)

Integration tests call Python API endpoints through `py_api` and assert end-to-end behavior from routing to serialization.
Most endpoint-focused tests under `tests/routers/openml/` use this style.

Characteristics:

- Exercise request/response handling via HTTP calls to the in-process FastAPI app.
- Use real dependency wiring (with test database connections injected via fixture overrides).
- Validate returned status codes and payloads as clients see them.

This layer is broader than direct function/database tests, but also has higher execution cost.

### 3) Direct database tests

Direct database tests call functions in `src/database/*` with `expdb_test`/`user_test` connections.
Examples are in `tests/database/`.

Characteristics:

- Focus on query behavior and returned records.
- Avoid HTTP/TestClient overhead.
- Validate persistence-layer behavior directly against the test database.

Use this layer when the change is primarily in SQL access or data retrieval logic.

### 4) Direct function tests

Direct function tests call router or dependency functions directly (without HTTP requests), often with lightweight fixtures and selective mocks.
Examples include tests that call functions such as `flow_exists(...)` or `get_dataset(...)` directly.

Characteristics:

- Validate function-level control flow and error handling.
- Can mock lower-level calls where appropriate.
- Keep runtime low compared with full TestClient tests.

These tests are useful for fast feedback on logic that does not require full HTTP-level verification.

## Performance tradeoffs

Fixture setup has measurable cost.
In existing measurements, creating `py_api` is significantly more expensive than direct function/database-level testing, and database fixtures also add overhead.

Practical implications:

- Prefer direct function or direct database tests when they can validate the behavior sufficiently.
- Reserve `py_api` usage for cases where endpoint-level integration behavior is the target.
- Keep migration tests focused, because they combine multiple expensive dependencies.

This keeps local feedback cycles fast while preserving endpoint and compatibility coverage where required.

## Design philosophy: limited mocking

Mocking is used to reduce runtime and isolate logic when full database interaction is not required.
At the same time, this repository keeps mocking limited by pairing it with real database coverage for the same entities/paths.

Why this balance is used:

- Mock-based tests are fast and targeted.
- Database-backed tests verify actual query/schema behavior.
- Together they reduce risk that mocked behavior diverges from real database behavior.

In short: mock for speed and focus, but keep real database tests for behavioral truth.

## Running tests

Run all tests (from the Python API container):

```bash
python -m pytest tests
```

Run a focused test module:

```bash
python -m pytest tests/routers/openml/datasets_test.py
```

Run by marker expression (example):

```bash
python -m pytest -m "not slow"
```

See `pyproject.toml` for current marker definitions (including `slow` and `mut`).
