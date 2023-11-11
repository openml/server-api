FROM mysql

COPY ./data /docker-entrypoint-initdb.d

# We want to bake the database state into the image, as it saves ~30 seconds on
# first start up. To do this, we run the default entry point script with `mysqld` as
# first argument, as this kickstarts the database initialisation. But this also forces
# `mysqld` to start after database initialization, which we don't want. So we automatically kill
# the process after 60 seconds, which should be enough time to initialize the database.
# c.f. https://github.com/docker-library/mysql/blob/master/8.0/docker-entrypoint.sh
RUN MYSQL_ROOT_PASSWORD=ok \
    timeout --preserve-status 60 \
    bash /usr/local/bin/docker-entrypoint.sh mysqld

RUN rm /docker-entrypoint-initdb.d/*
