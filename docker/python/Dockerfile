FROM python:3.14-bookworm

RUN apt-get update  \
    && apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m pip install uv

WORKDIR /python-api
COPY pyproject.toml .

RUN uv pip install -e ".[dev]"
COPY . /python-api


EXPOSE 8000
ENTRYPOINT ["python", "src/main.py"]
CMD ["--host", "0.0.0.0", "--reload"]
