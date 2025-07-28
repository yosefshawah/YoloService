from fastapi import FastAPI
from controllers.prediction import router as prediction_router
from controllers.stats import router as stats_router
from controllers.image import router as images_router
from controllers.labels import router as labels_router
from controllers.health import router as health_router


app = FastAPI()
app.include_router(prediction_router)
app.include_router(stats_router)
app.include_router(images_router)
app.include_router(labels_router)
app.include_router(health_router)



if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
