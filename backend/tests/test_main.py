"""
Test main application endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Ticolops API is running"
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ticolops-api"
    assert data["version"] == "1.0.0"