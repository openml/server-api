# Setting up the Development Environment

First, follow the [installation](installation.md#local-installation) instructions
for contributors to install a local fork with optional development dependencies.

## Pre-commit

We use [`pre-commit`](https://pre-commit.com) to ensure certain tools and checks are
ran before each commit. These tools perform code-formatting, linting, and more. This
makes the code more consistent across the board, which makes it easier to work with
each other's code and also can catch common errors. After installing it, it will
automatically run when you try to make a commit. Install it now and verify that all
checks pass out of the box:

```bash title="Install pre-commit and verify it works"
pre-commit install
pre-commit run all-files
```
Running the tool the first time may be slow as tools need to be installed,
and many tools will build a cache so subsequent runs are faster.
Under normal circumstances, running the pre-commit chain shouldn't take more than a few
seconds.

## Unit Tests

Our unit tests are written with the [`pytest`](https://pytest.org) framework.
An invocation could look like this: `pytest -v -x --lf`

```bash
python -m pytest -v -x --lf -m "not web"
```

Where `-v` show the name of each test ran, `-x` ensures testing stops on first failure,
`--lf` will first run the test(s) which failed last, and `-m "not web"` specifies
which tests (not) to run.

## Database
The server relies on a database connection, and we recommend to use a containerized
MySQL server regardless of your local development setup. This way there is no
variability in the database setup, and it is easy to reset to the same database state
other developers use.

Current workflow is to get a snapshot from the test server at test.openml.org/phpmyadmin,
and then host it in a local mysql container.
The databases are hardcoded to be accessible by user `root` with password `ok` at
`127.0.0.1:3306`.

TODO: Upload a docker image which has a test database included and can easily be run
without any local changes.

## Working from Docker
TODO

## YAML Validation
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
