# Setting up the development environment

First, follow the [installation](../installation.md#local-installation) instructions
for contributors to install a local fork with optional development dependencies.
Stop when you reach the section "Setting up a Database Server".

## Pre-commit

We use [`pre-commit`](https://pre-commit.com) to ensure certain tools and checks are
ran before each commit. These tools perform code-formatting, linting, and more. This
makes the code more consistent across the board, which makes it easier to work with
each other's code and also can catch common errors. After installing it, it will
automatically run when you try to make a commit. Install it now and verify that all
checks pass out of the box:

```bash title="Install pre-commit and verify it works"
pre-commit install
pre-commit run --all-files
```
Running the tool the first time may be slow as tools need to be installed,
and many tools will build a cache so subsequent runs are faster.
Under normal circumstances, running the pre-commit chain shouldn't take more than a few
seconds.


## Docker

With the projected forked, cloned, and installed, the easiest way to set up all
required services for development is through [`docker compose`](https://docs.docker.com/compose/).

### Starting containers

```bash
docker compose --profile all up -d
```

This will spin up 5 containers, as defined in the `docker-compose.yaml` file:

 - `openml-test-database`: this is a mysql database prepopulated with test data.
    It is reachable from the host machine with port `3306`, by default it is configured
    to have a root user with password `"ok"`.
 - `server-api-docs-1`: this container serves project documentation at `localhost:8000`.
    These pages are built from the documents in the `docs/` directory of this repository,
    whenever you edit and save a file there, the page will immediately be updated.
 - `openml-php-rest-api`: this container serves the old PHP REST API at `localhost:8002`.
    For example, visit [http://localhost:8002/api/v1/json/data/1](http://localhost:8002/api/v1/json/data/1)
    to fetch a JSON description of dataset 1.
 - `openml-elasticsearch`: Elastic search, required for the PHP REST API to function.
 - `openml-python-rest-api`: this container serves the new Python-based REST API at `localhost:8001`.
    For example, visit [http://localhost:8001/docs](http://localhost:8001/docs) to see
    the REST API documentation. Changes to the code in `src/` will be reflected in this
    container.

!!! note
    On arm-based Macs, you need to enable Rosetta emulation for Docker for the Elastic Search container to work.

We can now run the full test suite, which takes about 4 minutes:

```bash
docker exec openml-python-rest-api python -m pytest tests
```
There three important [test markers](https://docs.pytest.org/en/7.1.x/example/markers.html) to be aware of:

 - `php_api`: all tests that require the PHP API container. These are tests which
 - `python_api`: all tests that require the Python API container. That's almost all of them.
 - `slow`: for long-running tests. Currently only one test.

In many cases during development it's sufficient to either run with `not php_api and not slow` when initially adding the endpoint and implemting its response, or later `php_api and not slow` when working on the 'migration' tests that validate against the old PHP API.
The `not slow` is only needed if a slow test would be included in your test selection. In many cases, you might prefer to only run the specific tests (or test modules) that you are working on and excluding it through markers may be unnecessary.
Examples:

 - `docker exec openml-python-rest-api python -m pytest tests -m "not php_api and not slow"`, here the test selection is made primarily through markers. This command takes a few seconds.
 - `docker exec openml-python-rest-api python -m pytest tests/routers/openml/dataset_tag_test.py `, here the test selection is made through specifying the file with tests. Since this test file naturally includes neither migration tests (in `tests/routers/openml/migration`) nor the slow test (at `tests/routers/openml/datasets_list_datasets_test.py`), excluding tests through markers is unnecessary. This command takes a few seconds.


You don't always need every container, often just having a database and the Python-based
REST API may be enough. In that case, only specify those services:

```bash
docker compose --profile python up -d
```

Refer to the `docker compose` documentation for more uses.

!!! note
    We are working on making it easy to run tests from your local shell instead of the container ([#232](https://github.com/openml/server-api/pull/232)). This will likely be limited to the tests that do not need the PHP API. Our CI pipeline runs all tests.

### Connecting to containers

To connect to a container, run:

```bash
docker exec -it CONTAINER_NAME /bin/bash
```

where `CONTAINER_NAME` is the name of the container. If you are unsure of your container
name, then `docker container ls` may help you find it. Assuming the default container
names are used, you may connect to the Python-based REST API container using:

```bash
docker exec -it openml-python-rest-api /bin/bash
```

This is useful, for example, to run unit tests in the container:

```bash
python -m pytest -x -v -m "not php_api"
```

## Unit tests

Our unit tests are written with the [`pytest`](https://pytest.org) framework.
An invocation could look like this:

```bash
python -m pytest -v -x --lf -m "not php_api"
```

Where `-v` show the name of each test ran, `-x` ensures testing stops on first failure,
`--lf` will first run the test(s) which failed last, and `-m "not php_api"` specifies
which tests (not) to run (in this case, the tests that check against the PHP API).

The directory structure of our tests follows the structure of the `src/` directory.
For files, we follow the convention of _appending_ `_test`.
Try to keep tests as small as possible, and only rely on database and/or web connections
when absolutely necessary.

!!! Failure ""

    Instructions are incomplete. Please have patience while we are adding more documentation.


## YAML validation
The project contains various [`yaml`](https://yaml.org) files, for example to configure
`mkdocs` or to describe Github workflows. For these `yaml` files we can configure
automatic schema validation, to ensure that the files are valid without having to run
the server. This also helps with other IDE features like autocomplete. Setting this
up is not required, but incredibly useful if you do need to edit these files.
The following `yaml` files have schemas:

| File(s) | Schema URL |
| -- | -- |
| mkdocs.yml | https://squidfunk.github.io/mkdocs-material/schema.json |
| .pre-commit-config.yaml | https://json.schemastore.org/pre-commit-config.json |
| .github/workflows/*.yaml | https://json.schemastore.org/github-workflow |


=== "PyCharm"

    In PyCharm, these can be configured from `settings` > `languages & frameworks` >
    `Schemas and DTDs` > `JSON Schema Mappings`. There, add mappings per file or
    file pattern.

=== "VSCode"

    In VSCode, these can be configured from `settings` > `Extetions` >
    `JSON` > `Edit in settings.json`. There, add mappings per file or
    file pattern. For example:

      ```json
      "json.schemas": [
         {
               "fileMatch": [
                  "/myfile"
               ],
               "url": "schemaURL"
         }

      ]
      ```

## Connecting to another database
In addition to the database setup described in the [installation guide](../installation.md#setting-up-a-database-server),
we also host a database on our server which may be connected to that is available
to [OpenML core contributors](https://openml.org/about). If you are a core contributor
and need access, please reach out to one of the engineers in Eindhoven.

!!! Failure ""

    Instructions are incomplete. Please have patience while we are adding more documentation.
