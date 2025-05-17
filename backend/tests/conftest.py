"""Pytest configuration and fixtures for testing the Photo Portfolio backend."""
import os
import sys
from pathlib import Path

import pytest
from flask import Flask

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app as _app
from app import db


@pytest.fixture
def app():
    """Create and configure a new app instance for testing."""
    # Create a test config
    _app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
    })

    # Create the database and load test data
    with _app.app_context():
        db.create_all()

    yield _app

    # Clean up / reset resources here
    with _app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
