"""FastAPI dependencies shared by the routers."""

from src.core.settings import Settings, get_settings


async def settings() -> Settings:
    """Provide the cached application settings."""
    return get_settings()
