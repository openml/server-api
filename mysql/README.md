# Test Database

A

Files and documentation to create the test database container:

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


The test database the following special users:

| id | API key | Comments |
| -- | -- | -- |
| 1  | AD000000000000000000000000000000 | Administrator rights |
| 2  | 00000000000000000000000000000000 | Normal user |
| 16 | DA1A0000000000000000000000000000 | Normal user with private dataset with id 130 |
