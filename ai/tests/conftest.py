"""
pytest configuration for the AI service test suite.
Registers custom CLI options and marks.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--sarvam-key",
        action="store",
        default=None,
        help="Sarvam AI API key for live integration tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests as requiring live external credentials",
    )
