from fastapi import FastAPI
from routers.mldcat_ap.dataset import router as mldcat_ap_router
from routers.v1.datasets import router as datasets_router_old_format
from routers.v2.datasets import router as datasets_router

app = FastAPI()

app.include_router(datasets_router)
app.include_router(datasets_router_old_format)
app.include_router(mldcat_ap_router)
