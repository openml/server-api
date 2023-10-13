# Installing the Development Environment

*Current instructions written for Mac, but can be adapted for other operating systems.*

The OpenML server will be developed and maintained for the latest minor release of
Python (Python 3.12 as of writing).
You can install the dependencies locally or work from a Docker container (TODO).

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

## Local Installation
We recommend using [`pyenv`](https://github.com/pyenv/pyenv) if you are working with
multiple local Python versions.
We also recommend installing the dependencies into a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Then install the development dependencies:
```bash
python -m pip install -e ".[dev]"
pre-commit install
```
The [`pre-commit`](https://pre-commit.com) tool will ensure certain tools and checks are
ran before each commit. These tools perform code-formatting, linting, and more. This
makes the code more consistent across the board, which makes it easier to work with
each other's code and also can catch common errors. At this point all tests should pass:
`pre-commit run --all-files`. Running the tool the first time may be slow as tools need
to be installed, and many tools will build a cache so subsequent runs are faster.
Under normal circumstances, running the pre-commit chain shouldn't take more than a few
seconds.

Our unit tests are built for the [`pytest`](https://pytest.org) framework.
An invocation could look like this: `pytest -v -x --lf`
Where `-v` show the name of each test ran, `-x` ensures testing stops on first failure,
and `--lf` will first run the test(s) which failed last.


## Working from Docker
TODO
