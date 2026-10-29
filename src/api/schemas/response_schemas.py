"""Response schemas of the API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Possible health-check statuses."""

    OK = "OK!"
    DEGRADED = "DEGRADED"
