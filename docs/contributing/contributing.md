# Setting up the Development Environment

First, follow the [installation](../installation.md#local-installation) instructions
for contributors to install a local fork with optional development dependencies.
When setting up the database, follow the "Setting up a test database" instructions.

## Database
In addition to the database setup described in the [installation guide](../installation.md#setting-up-a-database-server),
we also host a database on our server which may be connected to that is available
to [OpenML core contributors](https://openml.org/about). If you are a core contributor
and need access, please reach out to one of the engineers in Eindhoven.

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
An invocation could look like this:

```bash
python -m pytest -v -x --lf -m "not web"
```

Where `-v` show the name of each test ran, `-x` ensures testing stops on first failure,
`--lf` will first run the test(s) which failed last, and `-m "not web"` specifies
which tests (not) to run.

## Building Documentation
We build our documentation with [`mkdocs-material`](https://squidfunk.github.io/mkdocs-material/).
All documentation pages are under the `docs` folder, and the configuration is found in
`mkdocs.yml`. Having installed the `docs` optional dependencies, you should be able
to locally build and serve the documentation:

```bash title="Serve documentation locally"
python -m mkdocs serve
```

You can browse the documentation by visiting `127.0.0.1:8000` in your browser.
The documentation pages will automatically rebuild when there are changes.

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
