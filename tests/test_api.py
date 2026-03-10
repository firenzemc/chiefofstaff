"""Tests for FastAPI endpoints."""

import os
import pytest
from httpx import AsyncClient, ASGITransport

from mainframe.main import app


@pytest.fixture
async def client(tmp_path):
    """Async client with all dependencies initialized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        import mainframe.main as m
        from mainframe.understanding.batch.intent_extractor import IntentExtractor
        from mainframe.understanding.batch.transcription import TranscriptionService
        from mainframe.router.engine import RoutingEngine
        from mainframe.audit.logger import AuditLogger
        from mainframe.audit.risk import RiskAssessor
        from mainframe.audit.store import AuditStore
        from mainframe.feedback.collector import FeedbackCollector
        from mainframe.connectors.mock import MockConnector
        from mainframe.memory.store import MemoryStore
        from mainframe.memory.matcher import CommitmentMatcher

        m._extractor = IntentExtractor()
        m._router = RoutingEngine()
        m._audit = AuditLogger()
        m._risk_assessor = RiskAssessor()
        m._feedback = FeedbackCollector()
        m._connector = MockConnector()
        m._transcriber = TranscriptionService()
        m._commitment_matcher = CommitmentMatcher()

        m._audit_store = AuditStore(str(tmp_path / "test_audit.db"))
        await m._audit_store.init()

        m._memory_store = MemoryStore(str(tmp_path / "test_memory.db"))
        await m._memory_store.init()

        yield c

        await m._audit_store.close()
        await m._memory_store.close()
        m._extractor = None
        m._router = None
        m._audit = None
        m._audit_store = None
        m._risk_assessor = None
        m._feedback = None
        m._connector = None
        m._transcriber = None
        m._memory_store = None
        m._commitment_matcher = None


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
        assert data["summary"]

    @pytest.mark.asyncio
    async def test_routes_carry_provenance(self, client):
        resp = await client.post("/analyze", json={
            "text": "Alice: We decided to launch next week.",
            "meeting_id": "prov-test",
        })
        data = resp.json()
        route = data["routes"][0]
        assert route["source_speaker"] == "Alice"
        assert route["source_text"]  # non-empty
        assert route["confidence"] > 0


class TestExecutionEndpoints:
    @pytest.mark.asyncio
    async def test_get_executions(self, client):
        # First create some data
        await client.post("/analyze", json={
            "text": "Alice: We decided to launch.\nBob: I'll prepare docs.",
            "meeting_id": "exec-test",
        })
        resp = await client.get("/executions/exec-test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meeting_id"] == "exec-test"
        assert len(data["executions"]) > 0
        # Verify execution records have risk info
        for exec_rec in data["executions"]:
            assert "risk_level" in exec_rec
            assert "risk_reason" in exec_rec
            assert "rollback_hint" in exec_rec

    @pytest.mark.asyncio
    async def test_pending_approvals_empty(self, client):
        resp = await client.get("/approvals/pending")
        assert resp.status_code == 200
        assert resp.json()["pending"] == []
