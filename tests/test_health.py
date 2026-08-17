"""Tests for the API health endpoint."""

import asyncio

from httpx import ASGITransport, AsyncClient

from story_companion.main import app


async def request_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/health")


def test_health_returns_ok() -> None:
    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
