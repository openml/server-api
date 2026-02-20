FROM python:3.14-bookworm

RUN apt-get update  \
    && apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
# Prepending the path here means that `python` invocations below use the virtual environment
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install uv

WORKDIR /app
COPY pyproject.toml .

RUN uv pip install -e ".[dev]"
COPY . /app

RUN mkdir /config
COPY ./src/config.toml /config/config.toml
ENV OPENML_REST_API_CONFIG_FILE_PATH=/config/config.toml
COPY ./docker/python/README.md /README.md

EXPOSE 8000
ENTRYPOINT ["python", "src/main.py"]
CMD ["--host", "0.0.0.0", "--reload"]
