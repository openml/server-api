FROM python:3.12-bookworm

RUN apt-get update  \
    && apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config

COPY . /python-api
WORKDIR /python-api

RUN python -m pip install --upgrade pip
RUN python -m pip install -e ".[dev]"

EXPOSE 8000
ENTRYPOINT ["uvicorn"]
CMD ["src.main:app", "--host", "0.0.0.0", "--reload"]
