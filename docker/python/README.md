# OpenML REST API
This is the work-in-progress Python-based REST API implementation for OpenML.
This should not be considered production ready.
New releases may contain breaking changes without deprecation warnings.

## Usage
The image is not inteded to be used as a standalone image.
Please reference either the docker compose file at [server-api](https://www.github.com/openml/server-api) for development purposes, or [services](https://www.github.com/openml/services) for deployment purposes.

## Configuration
Configuration is currently loaded from both a TOML file and a .env file.
Environment variables are used for configurations that either shouldn't be shared (secrets), or that inform how to load the configuration.
The TOML configuration file is used for all other settings.
By default both of these files are loaded from the `/config` directory.

### Configuration File
A default configuration is available for reference at `/config/config.toml`, and can be used as reference.

### Environment Variables
Environment variables are used for configurations that either shouldn't be shared (secrets), or that inform how to load the configuration:

 - `OPENML_REST_API_CONFIG_DIRECTORY`: points to the directory that contains configuration files (`config.toml`, `.env`) (default: `/config`)
 - `OPENML_REST_API_CONFIG_FILE`: points to the file that contains the TOML configuration (default: not set). If set, takes precedence over `OPENML_REST_API_CONFIG_DIRECTORY`.
 - `OPENML_REST_API_DOTENV_FILE`: points to the dot file that contains the environment variable settings (default: not set). If set, takes precedence over `OPENML_REST_API_CONFIG_DIRECTORY`.
 - `OPENML_DATABASES_OPENML_USERNAME`: username for connecting to the `openml` database (default: `root`)
 - `OPENML_DATABASES_OPENML_PASSWORD`: password for connecting to the `openml` database (default: `ok`)
 - `OPENML_DATABASES_EXPDB_USERNAME`: username for connecting to the `openml_expdb` database (default: `root`)
 - `OPENML_DATABASES_EXPDB_PASSWORD`: password for connecting to the `openml_expdb` database (default: `ok`)


## Repository
The code and dockerfile for this image are maintained [on GitHub](https://www.github.com/openml/server-api).
