# Installation

We currently only support running the REST API through a Docker container.
The REST API needs to be able to connect to a MySQL database with the OpenML "openml" and "openml_expdb" databases.
The `compose.yaml` file of this project defines these together out of the box.
This is useful for development purposes, but the database does not persist between restarts in the current configuration.
By default, the current code is also mounted into the Python REST API container (again, for development purposes).

It should suffice to run the services from a fresh clone by running `docker compose up python-api -d`.
If you want to make sure to bind the exposed container ports to the host machine then you will need to use the `compose.ports.yaml` file too (`docker compose -f compose.yaml -f compose.ports.yaml up python-api -d`).
The REST API will then be exposed on port 8001 on the host machine.
To visit the Swagger Docs which show REST API endpoint documentation, visit http://localhost:8001/docs.


Information for a production deployment will follow, in a nutshell you need to configure the REST API to connect to a persistent database,
which can be the one defined in `compose.yaml` if it has an appropriately mounted volume.
