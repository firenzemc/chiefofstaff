"""Tests for AuditStore (SQLite persistence)."""

import pytest
from mainframe.audit.store import AuditStore
from mainframe.audit.models import (
    ExecutionRecord, ExecutionStatus, PipelineRun, PipelineRunStatus, RiskLevel,
)


@pytest.fixture
async def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = AuditStore(db_path)
    await s.init()
    yield s
    await s.close()


def _make_run(run_id="run-1", meeting_id="m1"):
    return PipelineRun(
        run_id=run_id, meeting_id=meeting_id,
        status=PipelineRunStatus.STARTED, input_type="text", input_length=100,
    )


def _make_exec(record_id="exec-1", meeting_id="m1", run_id="run-1",
               status=ExecutionStatus.PENDING, risk=RiskLevel.LOW):
    return ExecutionRecord(
        record_id=record_id, meeting_id=meeting_id, run_id=run_id,
        intent_id="i1", intent_type="decision",
        source_speaker="Alice", source_text="Launch next week",
        source_timestamp=1.0, confidence=0.9,
        target="document", rule_id="r1",
        payload={"content": "Launch next week"},
        risk_level=risk, risk_reason="test",
        status=status, rollback_hint="DELETE paragraph",
    )


class TestPipelineRunPersistence:
    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        run = _make_run()
        await store.save_run(run)
        found = await store.get_run("run-1")
        assert found is not None
        assert found.run_id == "run-1"
        assert found.status == PipelineRunStatus.STARTED

    @pytest.mark.asyncio
    async def test_get_not_found(self, store):
        found = await store.get_run("nope")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_meeting(self, store):
        await store.save_run(_make_run("run-1", "m1"))
        await store.save_run(_make_run("run-2", "m1"))
        await store.save_run(_make_run("run-3", "m2"))
        runs = await store.get_runs_by_meeting("m1")
        assert len(runs) == 2

    @pytest.mark.asyncio
    async def test_upsert(self, store):
        run = _make_run()
        await store.save_run(run)
        run.status = PipelineRunStatus.COMPLETED
        run.intent_count = 5
        await store.save_run(run)
        found = await store.get_run("run-1")
        assert found.status == PipelineRunStatus.COMPLETED
        assert found.intent_count == 5


class TestExecutionRecordPersistence:
    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        rec = _make_exec()
        await store.save_execution(rec)
        found = await store.get_execution("exec-1")
        assert found is not None
        assert found.record_id == "exec-1"
        assert found.risk_level == RiskLevel.LOW
        assert found.rollback_hint == "DELETE paragraph"

    @pytest.mark.asyncio
    async def test_get_by_meeting(self, store):
        await store.save_execution(_make_exec("e1", "m1"))
        await store.save_execution(_make_exec("e2", "m1"))
        await store.save_execution(_make_exec("e3", "m2"))
        recs = await store.get_executions_by_meeting("m1")
        assert len(recs) == 2

    @pytest.mark.asyncio
    async def test_get_by_status(self, store):
        await store.save_execution(_make_exec("e1", status=ExecutionStatus.PENDING))
        await store.save_execution(_make_exec("e2", status=ExecutionStatus.AWAITING_APPROVAL))
        await store.save_execution(_make_exec("e3", status=ExecutionStatus.EXECUTED))
        pending = await store.get_executions_by_status(ExecutionStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].record_id == "e1"

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, store):
        await store.save_execution(_make_exec("e1", status=ExecutionStatus.PENDING))
        await store.save_execution(_make_exec("e2", status=ExecutionStatus.AWAITING_APPROVAL))
        approvals = await store.get_pending_approvals()
        assert len(approvals) == 1
        assert approvals[0].record_id == "e2"

    @pytest.mark.asyncio
    async def test_update_status(self, store):
        await store.save_execution(_make_exec("e1", status=ExecutionStatus.PENDING))
        updated = await store.update_execution_status(
            "e1", ExecutionStatus.EXECUTED,
            execution_result={"status": "ok"},
        )
        assert updated.status == ExecutionStatus.EXECUTED
        assert updated.execution_result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, store):
        result = await store.update_execution_status("nope", ExecutionStatus.EXECUTED)
        assert result is None

    @pytest.mark.asyncio
    async def test_payload_json_roundtrip(self, store):
        rec = _make_exec()
        rec.payload = {"title": "Launch", "assignee": "Alice", "nested": {"key": "val"}}
        await store.save_execution(rec)
        found = await store.get_execution("exec-1")
        assert found.payload == {"title": "Launch", "assignee": "Alice", "nested": {"key": "val"}}

    @pytest.mark.asyncio
    async def test_risk_level_persists(self, store):
        await store.save_execution(_make_exec("e1", risk=RiskLevel.CRITICAL))
        found = await store.get_execution("e1")
        assert found.risk_level == RiskLevel.CRITICAL
