from fastapi import FastAPI
from routers.datasets import router as datasets_router
from routers.mldcat_ap.dataset import router as mldcat_ap_router
from routers.old.datasets import router as datasets_router_old_format

app = FastAPI()

app.include_router(datasets_router)
app.include_router(datasets_router_old_format)
app.include_router(mldcat_ap_router)
