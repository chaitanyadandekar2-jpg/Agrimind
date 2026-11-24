"""AgriMind backend package.

Loads backend/.env into the process environment BEFORE any submodule is
imported. This matters because several modules read os.getenv() at import
time (llm_service, weather_service, vector_store, api/soil). Without this,
a key placed in .env is silently ignored and the app falls back to the
templated explanation even though the user configured OPENAI_API_KEY.

load_dotenv() does not override variables already set in the real
environment, so Docker/compose-provided values still win.
"""
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
