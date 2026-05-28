import pytest


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Override the DB-setup fixture — unit tests don't need a real database."""
    yield
