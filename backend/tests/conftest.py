import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure tests run offline and deterministically without external API timeouts."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
