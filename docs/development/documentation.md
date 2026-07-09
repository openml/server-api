# Documentation with mkdocs-material

Our documentation is built using [Zensical](https://zensical.org/).
It's made by the people that created Material for MkDocs, and is "backwards compatible" with that project (in fact, these docs were originally written for that framework).
Please refer to the ["Getting Started"](https://zensical.org/docs/get-started/)
pages of Zensical for a general overview on how to work with Zensical.

All documentation files are in the `docs/` folder, except for the configuration file
which is `mkdocs.yml` at the root of the repository.

For minor changes, it should be fine to edit the page directly on Github.
Commit the change to a separate branch (or fork) and you set up a pull request.
For larger changes, clone the repository as described in ["Getting the Code"](setup.md#getting-the-code).


=== "Docker"

    After cloning the repository, you may also build and serve the documentation through Docker:

    ```
    docker compose -f compose.yaml -f compose.ports.yaml up docs
    ```



=== "Local installation"

    Instead of installing all dependencies (with `python -m pip install -e ".[docs]"`),
    you may also install just the documentation dependencies:

    ```bash
    python -m pip install zensical
    ```

    You can then build and serve the documentation with

    ```bash
    python -m zensical serve
    ```

This will serve the documentation from the `docs/` directory to [http://localhost:8000/](http://localhost:8000/).
Any updates you make to files in that directory will be reflected on the website.
When you are happy with your changes, just commit and set up a pull request!

!! tip "Can't connect to Docker?"

    If the docker container is running but you cannot access it, it's likely that you did not correctly specify the compose files to include `compose.ports.yaml`.
