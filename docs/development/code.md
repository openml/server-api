The REST API is built with [FastAPI](https://fastapi.tiangolo.com/) for defining the endpoints, and [SQLAlchemy](https://docs.sqlalchemy.org/en/20/) for interaction with the database.

In the code base we aim to keep separate the interactions with the database (in the `database/` module) from the application logic and formatting of the endpoint (in `routers/` and `schemas/`, respectively).

```mermaid
treeView-beta
core/
  conversions.py  ## Common data conversion (e.g., unwrap single element list)
  errors.py  ## Map for all REST API errors
  formatting.py ## Common data formatting (e.g., split csv string to list)
  logging.py  ## Logging setup and middleware
  types.py  ## Common types, e.g., Identifier
database/  ## Anything that interacts with the database
  models/  ## ORM classes
    base.py ## Base classes every ORM class should inherit from
    ...
  engine.py  ## SQLAlchemy Engine Creation
  exceptions.py  ## Understandable Exceptions
  datasets.py ## CRUD operations on datasets
  ...
routers/  ## Defines Endpoints
  dependencies.py ## FastAPI Dependencies (e.g., authentication, database connections)
  datasets.py  ## Endpoints under `/datasets`
  ...
schemas/  ## Classes that define the REST API schema
  common.py ## Used across different subpaths
  datasets.py  ## Related to `/datasets` endpoints
  ...
config.py  ## For loading/accessing the configuration
config.toml  ## The configuration file
main.py ## API Entrypoint
```

!!! note "Exceptions"

    The initial development of the code base took place in sparse bursts of activity in a timespan of 3 years.
    This means that it wasn't always easy to work with full context, but also that views on the "correct" structure and patterns changed over time.
    Because of these factors, you may see deviations from the patterns described in this document, but we aim for consistent application of these ideas (or better ones :-)).


## Anatomy of an Endpoint

We show the general structure of an endpoint by way of example.
The following (simplified) code for tagging a dataset (from `src/routers/datasets.py`) has inline code annotation about what is going on.
Click the (+) icon for information.

```python  title="src/routers/datasets.py"

router = APIRouter(prefix="/datasets", tags=["datasets"])  # (1)!

@router.post(path="/tag")  # (2)!
async def tag_dataset(
    data_id: Annotated[Identifier, Body()],  # (3)!
    tag: Annotated[TagString, Body()],  # (4)!
    user: Annotated[User, Depends(fetch_user_or_raise)],  # (5)!
    expdb_db: Annotated[AsyncConnection, Depends(expdb_connection)],  # (6)!
) -> dict[str, dict[str, Any]]:  # (7)!
    """Add a tag to the dataset, this tag is publicly visible to all users."""  # (8)!
    try:
        await database.datasets.tag(data_id, tag, user_id=user.user_id, connection=expdb_db)  # (9)!
    except ForeignKeyConstraintError:
        msg = f"Dataset {data_id} not found."
        raise DatasetNotFoundError(msg, code=472) from None  # (10)!
    except DuplicatePrimaryKeyError:
        msg = f"Dataset {data_id} already tagged with {tag!r}."
        raise TagAlreadyExistsError(msg) from None

    logger.info("Dataset {data_id} tagged '{tag}'.", data_id=data_id, tag=tag) # (11)!

    tags = await database.datasets.get_tags_for(data_id, expdb_db)

    return {  # (12)!
        "data_tag": {"id": str(data_id), "tag": tags},
    }
```

1. All endpoints registered with this router automatically get the `/datasets` prefix and are shown together in the Swagger documentation.
2. To register an endpoint with the router, we need to specify the method (e.g., `get`, `post`) and the path (remember the path `/tag` will get the `/datasets` prefix!).
3. We can specify input parameters to the endpoint through defining parameters for the function. The type hint annotation will specify the type of the input (here, the custom type `Identifier`) and where to expect it (see ["Request Parameters"](https://fastapi.tiangolo.com/reference/parameters/)).
4. Custom types can be convenient for specifying common constraints. For example, an `Identifier` is always a positive integer. The `core/types.py` module is the place for common data types.
5. [Dependencies](https://fastapi.tiangolo.com/reference/dependencies/) may define common functions that are called by FastAPI. They may optionally define parameters that the user should supply. For user authentication, the `fetch_user` and `fetch_user_or_raise` dependencies will automatically request an API key from the client and load the corresponding user.
6. Another common use of dependencies is establishing a connection with the database.
7. The return type annotation is used by FastAPI to parse the return value of the function using Pydantic. You can create complex return types by defining Pydantic classes. These should be defined in the `schemas/` directory.
8. The docstring for the function is used by FastAPI in generating the OpenAPI spec. This means it will be publicly visible in the API documentation!
9. We delegate database operations to a `database/` submodule. Remember to `await` the response!
10. Errors raised by the REST API are defined in `core/errors.py`. The message will be returned to the client. The code matches PHP REST API output and will be deprecated in the future (see also the [Migration Guide](../migration.md#error-response-body)). An exception handler is set up in `main.py` to convert these Python error objects into proper [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) responses.
11. Log statements give observability to what's happening in the REST API (see [Logging](#logging)).
12. Return values are coerced into JSON form by FastAPI.

## Logging
We use [`loguru`](https://loguru.readthedocs.io/en/stable/) for logging.
A [middleware](https://fastapi.tiangolo.com/reference/middleware/) layer automatically provides the following context to each log entry (see `core/logging.py::add_request_context_to_log`):

 - a unique request identifier
 - the request method (such as `GET`, `POST`, ...)
 - the request path (such as `/datasets/tag`, ...)

Through middleware, three additional log entries are automatically written for each request:

 - information about the incoming request before processing the request
 - the response to the request after processing the request
 - processing time of the request after processing the request

!!! info "Take a peek"

    If you have a locally running API container, you can have a look at the logging produced with `docker compose logs python-api`.

It is generally useful to write additional log statements in your code, in particular when:

 - a user tries something they are not allowed to, log a warning message.
 - a user permutates the database (create, update, delete), log an info message.
 - something unexpected happens.

Additional messages may be added at your discretion, following these guidelines:

 - a log message should be atomic: it should not require other messages to understand (though context is available through the `request id`). This is necessary because the log may have messages from many concurrent requests so it's unlikely that subsequent log statements occur together in the log.
 - exclude sensitive data: these logs are going to be stored on the data in plain text.

!!! note "Absence of logging"

    During early development, the logging framework wasn't set up yet.
    Some endpoints may lack logging (other than the middleware).

### ORM usage

The project currently uses a mix of ORM and SQL queries to interact with the databases.
The adoption of ORM is recent and work in progress.
We haven't gone back through the codebase yet to ensure the general guidelines below are consistently applied.

Ultimately we plan to use ORM for all queries, unless we have the data to show that the ORM generated query is significantly slower than a raw SQL query.
However, so far we have used ORM only for operations on a single table or with a single join.
For queries that join multiple tables together, especially those with any kind of run data, we use an SQL query as a poorly generated query may significantly impact performance.
While we can investigate that as it comes up, we took the pragmatic approach of using the "good enough" queries from the PHP API.

???- question "Why we did not use ORM from the start"

    When we started the project two years ago, we chose not to use an ORM primarily because:

     - ORM constructed queries may be different from the ones PHP uses. Adding this change may make it harder to debug performance issues.
     - We will revise the database schema, and it seemed easier to make these changes if the schema is not also encoded in the code base any more than it needs to be.
     - Writing the SQL queries was a good way to get more familiar with the database.

    However, with the mixed approach these concerns are limited:

     - "Complex" queries may continue to use SQL queries. Simple operations such as `SELECT`, `UPDATE`, or `DELETE` statements from single tables should produce identical SQL queries.
     - We use [Reflection](https://docs.sqlalchemy.org/en/20/core/reflection.html#reflecting-database-objects) instead of declaring the tables entirely. We declare only as much of the database as we need to support the API, which means we are not encoding the database schema any more than a SQL query would.
      - We have gotten more familiar with the database during development already.
