"""Health-check route."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns service liveness. Always succeeds when the process is running."""
    return HealthResponse(status="ok", version="0.1.0")
