import pytest
from oberoon.app import Oberoon

@pytest.fixture
def app():
    return Oberoon()


@pytest.fixture
def test_client(app):
    return app.test_session()