"""FastAPI application entry point."""

from fastapi import FastAPI

from src.api.routers.v1 import health as health_router

app = FastAPI(title="Code Reviewer", version="0.1.0")


app.include_router(health_router.router)
