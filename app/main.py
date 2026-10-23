
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="E-commerce marketplace backend",
    version="0.1.0",
    debug=settings.DEBUG,
)


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
