# Test Database

The test database image is simply a [MySql image](https://hub.docker.com/_/mysql/) with
data already present. For general usage, such as setting a password or persisting data
to disk, see the linked MySQL image documentation.

The following command starts the database container:

```bash
docker run -e MYSQL_ROOT_PASSWORD=ok -p 3306:3306 -d --name testdb openml/test-database:latest
```
which sets:

 - `-e MYSQL_ROOT_PASSWORD=ok`: the root password is 'ok'
 - `-p 3306:3306`: makes the database accessible in the host on port 3306

You should be able to connect to it using `mysql`:
```bash
mysql --host 127.0.0.1 --port 3306 -uroot -pok
```
If you do not have `mysql` installed, you may refer to the MySQL image documentation on
how to use the image instead to connect over a docker network if you want to connect
with `mysql`.

The test database the following special users:

| id | API key | Comments |
| -- | -- | -- |
| 1  | AD000000000000000000000000000000 | Administrator rights |
| 2  | 00000000000000000000000000000000 | Normal user |
| 16 | DA1A0000000000000000000000000000 | Normal user with private dataset with id 130 |


## Creating the `openml/test-database` image

The following steps were taken to create the image:

 1. Create a dump for the current test database:

    ```text
    mysqldump -u root --add-drop-database --databases openml_expdb --result-file=openml_expdb.sql -p
    mysqldump -u root --add-drop-database --databases openml --ignore_table=openml.login_attempts --result-file=openml.sql -p
    ```

    `login_attempts` is a legacy table which is not used in production but has a few rows in the current test database.

 2. Copy over the files to the local directory:

    ```bash
    scp USERNAME@test.openml.org:/path/to/openml-anonimized.sql data/openml.sql
    scp USERNAME@test.openml.org:/path/to/openml_expdb.sql data/openml_expdb.sql
    ```

 3. Anonimize the sensitive information from the openml database:
    ```text
    python openml-kube/k8s_manifests/mysql/migration/anonimize-openml-db.py --input=openml.sql
    ```
    This produces `openml-anonimized.sql` which has user data replaced by fake data.

 4. Build and publish the docker image:

    ```bash
    docker build --tag openml/test-database:latest -f Dockerfile .
    docker push openml/test-database:latest
    ```
