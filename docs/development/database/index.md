# Database Schema

The OpenML server uses two MySQL databases:

- **[openml](openml.md)** — Core platform database for user accounts, file storage, access control, and forum threads.
- **[openml_expdb](openml_expdb.md)** — Experiment database storing datasets, tasks, flows (implementations), runs, evaluations, and studies.

These documentation pages describe their current schemas.
There are several tables which are no longer in use, these are mentioned but not described.
The plan is to revise the database schema after we sunset the PHP API, to avoid having to make changes to two APIs.

When launching the services as described in ["Development Environment"](../setup.md#docker), you can access the mysql server with both databases using `docker compose exec database mysql -uroot -pok`.

## ORM usage

The project currently uses a mix of ORM and SQL queries to interact with the databases.
The adoption of ORM is recent and work in progress.
We haven't gone back through the codebase yet to ensure the general guidelines below are consistently applied.

Ultimately we plan to use ORM for all queries, unless we have the data to show that the ORM generated query is significantly slower than a raw SQL query.
However, so far we have used ORM only for operations on a single table or with a single join.
For queries that join multiple tables together, especially those with any kind of run data, we use an SQL query as a poorly generated query may significantly impact performance.
While we can investigate that as it comes up, we took the pragmatic approach of using the "good enough" queries from the PHP API.

### Why we did not use ORM from the start
When we started the project two years ago, we chose not to use an ORM primarily because:

 - ORM constructed queries may be different from the ones PHP uses. Adding this change may make it harder to debug performance issues.
 - We will revise the database schema, and it seemed easier to make these changes if the schema is not also encoded in the code base any more than it needs to be.
 - Writing the SQL queries was a good way to get more familiar with the database.

However, with the mixed approach these concerns are limited:

 - "Complex" queries may continue to use SQL queries. Simple operations such as `SELECT`, `UPDATE`, or `DELETE` statements from single tables should produce identical SQL queries.
 - We use [Reflection](https://docs.sqlalchemy.org/en/20/core/reflection.html#reflecting-database-objects) instead of declaring the tables entirely. We declare only as much of the database as we need to support the API, which means we are not encoding the database schema any more than a SQL query would.
  - We have gotten more familiar with the database during development already.
