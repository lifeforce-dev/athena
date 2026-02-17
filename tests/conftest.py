"""Shared test configuration.

Sets required environment variables before any application code is imported.
This file is processed by pytest before test modules, ensuring create_app()
guards pass during collection.
"""
import os

os.environ.setdefault("ATHENA_JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("ATHENA_CORS_ORIGINS", '["http://localhost:5173"]')
