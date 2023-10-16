# Installation

*Current instructions written for Mac, but can be adapted for other operating systems.*

The OpenML server will be developed and maintained for the latest minor release of
Python (Python 3.12 as of writing).
You can install the dependencies locally or work from a Docker container (TODO).

!!! tip "Use `pyenv` to manage Python installations"

    We recommend using [`pyenv`](https://github.com/pyenv/pyenv) if you are working with
    multiple local Python versions.

## Local Installation


=== "For Users"

    If you don't plan to make code changes, you can install directly from Github.
    We recommend to install the OpenML server and its dependencies into a new virtual
    environment.
    ```bash  title="Installing the project into a new virtual environment"
    python -m venv venv
    source venv/bin/activate

    python -m pip install git+https://github.com/openml/server-api.git
    ```
    If you do plan to make code changes, we recommend you follow the instructions
    under the "For Contributors" tab, even if you do not plan to contribute your
    changes back into the project.


=== "For Contributors"

    If you plan to make changes to this project, it will be useful to install
    the project from a cloned fork. To fork the project, go to our
    [project page](https://github.com/openml/server-api) and click "fork".
    This makes a copy of the repository under your own Github account.
    You can then clone your own fork (replace `USER_NAME` with your Github username):

    ```bash title="Cloning your fork"
    git clone https://github.com/USER_NAME/server-api.git
    cd server-api
    ```

    Then we can install the project into a new virtual environment in edit mode:

    ```bash title="Installing the project into a new virtual environment"
    python -m venv venv
    source venv/bin/activate

    python -m pip install -e ".[dev,docs]"
    ```
    Note that this also installs optional dependencies for development and documentation
    tools. We require this for contributors, but we also highly recommend it anyone
    that plans to make code changes.

Before we run the REST API server, we must first set up a database server, and configure
the REST API to connect to it.

## Setting up a Database Server

...

## Configuring the REST API Server

...
