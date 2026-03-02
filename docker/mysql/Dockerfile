FROM mysql:8.4

COPY ./data /docker-entrypoint-initdb.d

# We want to bake the database state into the image, as it saves ~30 seconds on
# first start up. To do this, we run the default entry point script with `mysqld` as
# first argument, as this kickstarts the database initialisation. But this also forces
# `mysqld` to start after database initialization, which we don't want. So we automatically kill
# the process after 180 seconds, which should be enough time to initialize the database.
# c.f. https://github.com/docker-library/mysql/blob/master/8.0/docker-entrypoint.sh
#
# I am a little unsure about the next bit, but it works:
# Multi-architecture builds will execute this within the same build environment,
# which means each architecture needs to host their `mysqld` on their own port
# otherwise one of the two will error during the build process as the port is already taken.
RUN if [ $(uname -m) = "x86_64" ]; then export PORT=3036; else export PORT=30306; fi \
    && MYSQL_ROOT_PASSWORD=ok \
    timeout --preserve-status 180 \
    bash /usr/local/bin/docker-entrypoint.sh mysqld --port=${PORT}

RUN rm /docker-entrypoint-initdb.d/*
