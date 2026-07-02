"""Test fixtures. All tests run fully offline and deterministic."""

import os

# Force offline mode BEFORE any src import reads Config.
os.environ["BLITZ_OFFLINE"] = "1"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("SERPAPI_API_KEY", None)

import pytest  # noqa: E402

from src.core.state_manager import KnowledgeArchive  # noqa: E402


@pytest.fixture
def archive(tmp_path):
    return KnowledgeArchive(filepath=str(tmp_path / "knowledge.jsonl"))
