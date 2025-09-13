from fastapi import FastAPI
from controllers.prediction import router as prediction_router
from controllers.stats import router as stats_router
from controllers.image import router as images_router
from controllers.labels import router as labels_router
from controllers.health import router as health_router
from database.db import init_db
from multiprocessing import Process
from typing import Optional
from services.worker import (
    start_receive_worker,
    stop_receive_worker,
    start_billing_consumer_thread,
    start_analytics_consumer_thread,
)


app = FastAPI()
init_db()
app.include_router(prediction_router)
app.include_router(stats_router)
app.include_router(images_router)
app.include_router(labels_router)
app.include_router(health_router)

_worker_process: Optional[Process] = None
_billing_thread = None
_analytics_thread = None


@app.on_event("startup")
async def _app_startup() -> None:
    global _worker_process, _billing_thread, _analytics_thread
    _worker_process = start_receive_worker() # pragma: no cover
    _billing_thread = start_billing_consumer_thread() # pragma: no cover
    _analytics_thread = start_analytics_consumer_thread() # pragma: no cover


@app.on_event("shutdown")
async def _app_shutdown() -> None:
    global _worker_process
    stop_receive_worker(_worker_process)
    _worker_process = None



if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
