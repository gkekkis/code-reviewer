"""Health-check endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.api.dependencies import settings
from src.core.settings import Settings

router = APIRouter(prefix="/v1", tags=["Health-Check"])


@router.get("/health")
async def health(settings: Annotated[Settings, Depends(settings)]):
    """Report that the service is up."""
    return JSONResponse(content="OK!", status_code=status.HTTP_200_OK)
