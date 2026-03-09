"""Tests for the audit logger."""

import pytest
from mainframe.audit.logger import AuditLogger
from mainframe.audit.models import PipelineRunStatus


class TestAuditLogger:
    @pytest.mark.asyncio
    async def test_start_run(self):
        logger = AuditLogger()
        run = await logger.start_run("m1", "text", 500)
        assert run.meeting_id == "m1"
        assert run.status == PipelineRunStatus.STARTED
        assert run.input_type == "text"
        assert run.input_length == 500
        assert run.run_id.startswith("run-")

    @pytest.mark.asyncio
    async def test_complete_run(self):
        logger = AuditLogger()
        run = await logger.start_run("m1", "text", 100)
        completed = await logger.complete_run(run.run_id, intent_count=5, route_count=3)
        assert completed.status == PipelineRunStatus.COMPLETED
        assert completed.intent_count == 5
        assert completed.route_count == 3
        assert completed.completed_at is not None
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_fail_run(self):
        logger = AuditLogger()
        run = await logger.start_run("m1", "text", 100)
        failed = await logger.fail_run(run.run_id, "LLM timeout")
        assert failed.status == PipelineRunStatus.FAILED
        assert failed.error == "LLM timeout"
        assert failed.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status(self):
        logger = AuditLogger()
        run = await logger.start_run("m1", "text", 100)
        updated = await logger.update_status(run.run_id, PipelineRunStatus.EXTRACTING)
        assert updated.status == PipelineRunStatus.EXTRACTING

    @pytest.mark.asyncio
    async def test_get_run(self):
        logger = AuditLogger()
        run = await logger.start_run("m1", "text", 100)
        found = await logger.get_run(run.run_id)
        assert found is not None
        assert found.run_id == run.run_id

    @pytest.mark.asyncio
    async def test_get_run_not_found(self):
        logger = AuditLogger()
        found = await logger.get_run("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_meeting(self):
        logger = AuditLogger()
        await logger.start_run("m1", "text", 100)
        await logger.start_run("m1", "text", 200)
        await logger.start_run("m2", "text", 300)

        m1_runs = await logger.get_by_meeting("m1")
        assert len(m1_runs) == 2

    @pytest.mark.asyncio
    async def test_complete_nonexistent_returns_none(self):
        logger = AuditLogger()
        result = await logger.complete_run("nope", 0, 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_fail_nonexistent_returns_none(self):
        logger = AuditLogger()
        result = await logger.fail_run("nope", "err")
        assert result is None
