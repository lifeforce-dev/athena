from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


class TestDesignsV1Endpoint:
    def test_design_hub_v1_returns_sections(self):
        with TestClient(app) as client:
            resp = client.get("/designs/v1")

        assert resp.status_code == 200
        body = resp.text
        assert "Design Review Hub" in body
        assert "Claude" in body
        assert "GPT" in body
        assert "Gemini" in body
        assert "/designs/v1/claude/01-timeline-river.html" in body
        assert "/designs/v1/gpt/arcane-ledger.html" in body
        assert "/designs/v1/gemini/01-neon-hud.html" in body

    def test_design_file_v1_serves_html(self):
        with TestClient(app) as client:
            resp = client.get("/designs/v1/gpt/arcane-ledger.html")

        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_unknown_provider_returns_404(self):
        with TestClient(app) as client:
            resp = client.get("/designs/v1/unknown/sample.html")

        assert resp.status_code == 404
