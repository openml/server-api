# OpenML Docker Images
This directory contains the files and information to build the following 5 images:

 - [openml/test-database](https://hub.docker.com/r/openml/test-database): the official
    [mysql](https://hub.docker.com/_/mysql) image, but with the test database already
    baked into the image to significantly reduce startup times.
 - docs: the official [mkdocs-material](https://hub.docker.com/r/squidfunk/mkdocs-material)
    image but with additional plugins installed required for building the documentation
    in this project's `/doc` directory.
 - [openml/php-rest-api](https://hub.docker.com/r/openml/php-rest-api): image with the
    php back-end code, but ran on [feature/elasticsearch8](https://github.com/openml/openml/tree/feature/elasticsearch8)
    branch.
 - python-api: an image of this project, to facilitate development on any platform.
 - [openml/elasticsearch8-prebuilt](https://hub.docker.com/r/openml/elasticsearch8-prebuilt):
    the default elasticsearch image, but with indices already built on the test database
    through invocation of the old php code.

Between the prebuilt indices and the baked-in database, when all images have already been
pulled, a `docker compose up` step should only take seconds. 🚀

## Building `openml/elasticsearch8-prebuilt`
The `openml/elasticsearch8-prebuilt` is not made with a Dockerfile, because it requires
steps of running containers, which to the best of my knowledge is not facilitated by
docker (not even through [multi-stage builds](https://docs.docker.com/build/building/multi-stage/)).
So, instead we build the container state locally and then use [`docker commit`](https://docs.docker.com/engine/reference/commandline/commit/).

1. run `docker compose up`, but with the `elasticsearch` service pointing to
    `docker.elastic.co/elasticsearch/elasticsearch:8.10.4` instead of `openml/elasticsearch8-prebuilt`.
2. build the indices from the `php-api` container:

   1. Connect to the container: `docker exec -it server-api-php-api-1 /bin/bash`
   2. (optional) Edit `/var/www/openml/index.php` and set L56 to `development` instead of `production`,
       this will show progress of building the indices, or print out any error that may occur.
   3. Build the indices: `php /var/www/openml/index.php cron build_es_indices`
   4. Exit the container with `exit`.

3. Make a commit of the elastic search container with prebuilt indices: `docker commit elasticsearch openml/elasticsearch8-prebuilt`
4. Push the image created by the commit: `docker push openml/elasticsearch8-prebuilt`
