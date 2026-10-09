"""pytest configuration."""
import pytest


# Allow pytest-asyncio to automatically handle async tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
