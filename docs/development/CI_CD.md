We have the following GitHub actions:

 - `.github/workflows/docker-publish.yml`: Build and publish a new Docker image to [our DockerHub repository](https://hub.docker.com/r/openml/rest-api) on release.
 - `.github/workflows/docs.yml`: Build and deploy these documentation pages on a merge to the main branch.
 - `.github/workflows/tests.yml`: Run all tests on pull requests and a push to main, pushes code coverage reports to Codecov.

Additionally, we also have the following services configured:

 - `.pre-commit-config.yaml`: For local pre-commits, but also used by pre-commit.ci on pull requests.
 - `codecov.yaml`: For providing code coverage reports on pull requests.
 - `CodeRabbit` and `Sourcery AI` for automated code reviews.

 !!! example "On AI code reviews"

    We are currently experimenting with AI code reviews.
    For all their flaws in code generation, these bots do regularly point out typos and sometimes bring in context beyond the authors' familiarity.
    They also make poor suggestions, but those are typically easy to identify and ignore.
