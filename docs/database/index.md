# Database Schema

The OpenML server uses two MySQL databases:

- **[openml](openml.md)** — Core platform database for user accounts, file storage, access control, and forum threads.
- **[openml_expdb](openml_expdb.md)** — Experiment database storing datasets, tasks, flows (implementations), runs, evaluations, and studies.

These documentation pages describe their current schemas.
There are several tables which are no longer in use, these are mentioned but not described.
The plan is to revise the database schema after we sunset the PHP API, to avoid having to make changes to two APIs.

When launching the services as described in ["Installation"](../installation.md), you can access the mysql server with both databases using `docker compose exec database mysql -uroot -pok`.

## Why we use queries instead of an ORM tool
There are two main reasons why we do not use an ORM tool *yet*.

First, we want to keep queries close to the original PHP implementation.
Not using an ORM makes it natural to stick with similar or identical queries that the PHP API uses.
Introducing an ORM, and having it construct queries for us, adds an extra layer of changes.
Performance issues may be harder to trace down if they arise.

Second, we will likely revise the database schema significantly after the PHP API is sunset.
The current schema is over a decade old and contains design decisions based on expected future use or features
and other decisions which we may want to revise based on our experience running OpenML.
It seems easier to support those changes when we do not yet use an ORM tool.

The expectation is that we will move to using an ORM tool once the schema is revised and stable.
