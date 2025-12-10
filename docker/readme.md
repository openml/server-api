# OpenML Docker Images
This directory contains the files and information to build the following 5 images:

 - [openml/test-database](https://hub.docker.com/r/openml/test-database): the official
    [mysql](https://hub.docker.com/_/mysql) image, but with the test database already
    baked into the image to significantly reduce startup times.
 - docs: the official [mkdocs-material](https://hub.docker.com/r/squidfunk/mkdocs-material)
    image but with additional plugins installed required for building the documentation
    in this project's `/doc` directory.
 - python-api: an image of this project, to facilitate development on any platform.

Between the prebuilt indices and the baked-in database, when all images have already been
pulled, a `docker compose up` step should only take seconds. 🚀

## Building for multiple platforms

Following Docker's "[multi-platform images](https://docs.docker.com/build/building/multi-platform/)"
documentation, we can build multi-platform images in a few simple steps:

1. Only the first time, create a docker-container driver: `docker buildx create --name container --driver=docker-container`
2. Use `docker buildx` to build for multiple target platforms: `docker buildx build --builder=container --platform=linux/amd64,linux/arm64 -t openml/test-database docker/mysql`
3. If you want to push the images to Dockerhub, run the command above with the added `--push` option.
