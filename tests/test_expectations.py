"""Tests for the expectation-setting surfaces: mode reporting everywhere.

The contract: the user must always be able to tell which capability mode
they are in and what to expect, from any surface (CLI, API, report text).
"""

from src.core.config import Config
from src.core.orchestrator import BLITZOrchestrator


class TestCapabilityMode:
    def test_offline_mode_reported(self):
        # conftest sets BLITZ_OFFLINE=1 for all tests
        mode = Config.capability_mode()
        assert mode["mode"] == "offline"
        assert mode["label"]
        assert mode["expect"]
        assert mode["upgrade"]

    def test_all_modes_have_required_fields(self, monkeypatch):
        combos = [
            (False, "", "", "heuristic"),
            (False, "sk-x", "", "llm_only"),
            (False, "", "serp-x", "search_only"),
            (False, "sk-x", "serp-x", "full"),
            (True, "sk-x", "serp-x", "offline"),
        ]
        for offline, llm_key, serp_key, expected in combos:
            monkeypatch.setattr(Config, "OFFLINE_MODE", offline)
            monkeypatch.setattr(Config, "OPENAI_API_KEY", llm_key)
            monkeypatch.setattr(Config, "ANTHROPIC_API_KEY", "")
            monkeypatch.setattr(Config, "SERPAPI_API_KEY", serp_key)
            mode = Config.capability_mode()
            assert mode["mode"] == expected
            for field in ("label", "reasoning", "evidence", "expect", "upgrade"):
                assert field in mode

    def test_full_mode_needs_no_upgrade(self, monkeypatch):
        monkeypatch.setattr(Config, "OFFLINE_MODE", False)
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-x")
        monkeypatch.setattr(Config, "SERPAPI_API_KEY", "serp-x")
        assert Config.capability_mode()["upgrade"] == ""


class TestReportStatesMode:
    def test_response_includes_mode_banner(self, archive):
        result = BLITZOrchestrator(archive=archive).run("Mode banner check")
        assert result["success"]
        assert "Mode:" in result["state"]["response"]


class TestCLIStatus:
    def test_status_output(self, archive, capsys):
        from src.cli import print_status

        print_status(archive)
        out = capsys.readouterr().out
        assert "Mode:" in out
        assert "Expect:" in out
        assert "Knowledge archive" in out
        assert "Cost guards" in out


class TestHealthEndpoint:
    def test_health_reports_mode_and_expectations(self, tmp_path):
        from fastapi.testclient import TestClient

        from src.api import routes

        client = TestClient(routes.app)
        data = client.get("/health").json()
        assert data["mode"]
        assert data["mode_label"]
        assert data["expectations"]
        assert data["cost_guards"]["max_iterations"] >= 1
