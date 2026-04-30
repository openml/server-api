# Database Schema

The OpenML server uses two MySQL databases:

- **[openml](openml.md)** — Core platform database for user accounts, file storage, access control, and forum threads.
- **[openml_expdb](openml_expdb.md)** — Experiment database storing datasets, tasks, flows (implementations), runs, evaluations, and studies.

These documentation pages describe their current schemas.
There are several tables which are no longer in use, these are mentioned but not described.
The plan is to revise the database schema after we sunset the PHP API, to avoid having to make changes to two APIs.

When launching the services as described in ["Installation"](../installation.md), you can access the mysql server with both databases using `docker compose exec database mysql -uroot -pok`.
