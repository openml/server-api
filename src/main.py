import argparse

import uvicorn
from fastapi import FastAPI
from routers.mldcat_ap.dataset import router as mldcat_ap_router
from routers.v1.datasets import router as datasets_router_v1_format
from routers.v1.qualities import router as qualities_router
from routers.v1.tasktype import router as ttype_router
from routers.v2.datasets import router as datasets_router


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    uvicorn_options = parser.add_argument_group(
        "uvicorn",
        "arguments forwarded to uvicorn",
    )
    uvicorn_options.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload",
    )
    uvicorn_options.add_argument(
        "--host",
        default="127.0.0.1",
        type=str,
        help="Bind socket to this host.",
    )
    uvicorn_options.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Bind socket to this port. If 0, an available port will be picked.",
    )
    return parser.parse_args()


def create_api() -> FastAPI:
    app = FastAPI()

    app.include_router(datasets_router)
    app.include_router(datasets_router_v1_format)
    app.include_router(qualities_router)
    app.include_router(mldcat_ap_router)
    app.include_router(ttype_router)
    return app


def main() -> None:
    args = _parse_args()
    uvicorn.run(
        app="main:create_api",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
