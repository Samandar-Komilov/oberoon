import httpx
import pytest

from oberoon import Oberoon


@pytest.fixture
async def app():
    return await Oberoon()


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
