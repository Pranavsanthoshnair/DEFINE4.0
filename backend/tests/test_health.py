"""
Basic smoke tests for the health endpoint.
Run: pytest backend/tests/ -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_campaigns_list_returns_empty_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/campaigns/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_campaigns_get_nonexistent_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/campaigns/nonexistent-id")
    assert response.status_code == 404
