from fastapi import FastAPI
from routers import datasets
from routers.mldcat_ap.dataset import router as mldcat_ap_router

app = FastAPI()

app.include_router(datasets.router)
app.include_router(datasets.router_old_format)
app.include_router(mldcat_ap_router)
