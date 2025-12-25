# Installation

The primary way to run this service is through a Docker container.
The REST API needs to be able to connect to a MySQL database with the OpenML "openml" and "openml_expdb" databases.
The `docker-compose.yaml` file of this project defines these together out of the box.
This is useful for development purposes, but the database does not persist between restarts in the current configuration.
By default, the current code is also mounted into the Python REST API container (again, for development purposes).

For development, it should suffice to run the services from a fresh clone by running `docker compose --profile "python" up -d`.
The REST API will be exposed on port 8001 on the host machine. To visit the Swagger Docs, visit http://localhost:8001/docs.

Once the containers are started, you can run tests with `docker exec -it openml-python-rest-api python -m pytest -m "not php_api" tests`.
For migration testing, which compares output of the Python based REST API with the old PHP based one, also start the PHP server (`docker compose --profile "php" --profile "python" up -d`) and include tests with the `php_api` marker/fixture: `docker exec -it openml-python-rest-api python -m pytest tests`.

!!! note

    The PHP REST API needs Elastic Search. In some cases, it also needs the ES indices to be built.
    The current set up does not automatically build ES indices, because that takes a long time.
    When we start testing more upload functionality, for which the PHP API needs built indices, we'll work on an ES image with prebuilt indices.

Information for a production deployment will follow, in a nutshell you need to configure the REST API to connect to a persistent database,
which can be the one defined in `docker-compose.yaml` if has an appropriately mounted volume.
