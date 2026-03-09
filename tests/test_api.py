"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from mainframe.main import app


@pytest.fixture
async def client():
    """Async client that triggers lifespan events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Manually trigger lifespan startup
        import mainframe.main as m
        from mainframe.understanding.batch.intent_extractor import IntentExtractor
        from mainframe.understanding.batch.transcription import TranscriptionService
        from mainframe.router.engine import RoutingEngine
        from mainframe.audit.logger import AuditLogger
        from mainframe.feedback.collector import FeedbackCollector
        from mainframe.connectors.mock import MockConnector

        m._extractor = IntentExtractor()
        m._router = RoutingEngine()
        m._audit = AuditLogger()
        m._feedback = FeedbackCollector()
        m._connector = MockConnector()
        m._transcriber = TranscriptionService()

        yield c

        # Reset globals
        m._extractor = None
        m._router = None
        m._audit = None
        m._feedback = None
        m._connector = None
        m._transcriber = None


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_success(self, client):
        resp = await client.post("/analyze", json={
            "text": "Alice: We decided to launch.\nBob: I'll prepare the docs.",
            "meeting_id": "api-test-1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["meeting_id"] == "api-test-1"
        assert "intents" in data
        assert "routes" in data
        assert "run_id" in data
        assert len(data["intents"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_empty_text(self, client):
        resp = await client.post("/analyze", json={"text": ""})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_whitespace_only(self, client):
        resp = await client.post("/analyze", json={"text": "   \n  "})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_generates_meeting_id(self, client):
        resp = await client.post("/analyze", json={
            "text": "Alice: Hello world.",
        })
        assert resp.status_code == 200
        assert resp.json()["meeting_id"].startswith("meeting-")

    @pytest.mark.asyncio
    async def test_analyze_response_has_routes(self, client):
        resp = await client.post("/analyze", json={
            "text": "Alice: We decided to launch.\nBob: I'll prepare docs.",
            "meeting_id": "route-test",
        })
        data = resp.json()
        assert len(data["routes"]) > 0
        for route in data["routes"]:
            assert "intent_id" in route
            assert "target" in route
            assert "rule_id" in route

    @pytest.mark.asyncio
    async def test_analyze_has_summary(self, client):
        resp = await client.post("/analyze", json={
            "text": "Alice: We decided to launch.\nBob: Sounds good.",
        })
        data = resp.json()
        assert data["summary"]  # non-empty
