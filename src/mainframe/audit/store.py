"""
SQLite-backed persistent store for audit records.

Stores both PipelineRun and ExecutionRecord.
Uses aiosqlite for async access — single-writer is fine for our workload.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .models import (
    ExecutionRecord,
    ExecutionStatus,
    PipelineRun,
    PipelineRunStatus,
    RiskLevel,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          TEXT PRIMARY KEY,
    meeting_id      TEXT NOT NULL,
    status          TEXT NOT NULL,
    input_type      TEXT NOT NULL,
    input_length    INTEGER NOT NULL,
    intent_count    INTEGER DEFAULT 0,
    route_count     INTEGER DEFAULT 0,
    error           TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    duration_ms     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_runs_meeting ON pipeline_runs(meeting_id);

CREATE TABLE IF NOT EXISTS execution_records (
    record_id        TEXT PRIMARY KEY,
    meeting_id       TEXT NOT NULL,
    run_id           TEXT NOT NULL,

    intent_id        TEXT NOT NULL,
    intent_type      TEXT NOT NULL,
    source_speaker   TEXT NOT NULL,
    source_text      TEXT NOT NULL,
    source_timestamp REAL NOT NULL,
    confidence       REAL NOT NULL,

    target           TEXT NOT NULL,
    rule_id          TEXT NOT NULL,
    payload          TEXT NOT NULL,     -- JSON

    risk_level       TEXT NOT NULL DEFAULT 'low',
    risk_reason      TEXT DEFAULT '',
    approved_by      TEXT,
    approved_at      TEXT,
    expires_at       TEXT,

    status           TEXT NOT NULL DEFAULT 'pending',
    executed_at      TEXT,
    execution_result TEXT,              -- JSON

    rollback_hint    TEXT DEFAULT '',
    rolled_back_at   TEXT,
    rollback_result  TEXT,              -- JSON

    created_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exec_meeting ON execution_records(meeting_id);
CREATE INDEX IF NOT EXISTS idx_exec_status  ON execution_records(status);
CREATE INDEX IF NOT EXISTS idx_exec_run     ON execution_records(run_id);
"""


class AuditStore:
    """Async SQLite store for audit data."""

    def __init__(self, db_path: str = "mainframe_audit.db") -> None:
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # PipelineRun persistence
    # ------------------------------------------------------------------

    async def save_run(self, run: PipelineRun) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO pipeline_runs
               (run_id, meeting_id, status, input_type, input_length,
                intent_count, route_count, error, started_at, completed_at, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id, run.meeting_id, run.status.value, run.input_type,
                run.input_length, run.intent_count, run.route_count, run.error,
                run.started_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.duration_ms,
            ),
        )
        await self._db.commit()

    async def get_run(self, run_id: str) -> Optional[PipelineRun]:
        cur = await self._db.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        )
        row = await cur.fetchone()
        return self._row_to_run(row, cur.description) if row else None

    async def get_runs_by_meeting(self, meeting_id: str) -> list[PipelineRun]:
        cur = await self._db.execute(
            "SELECT * FROM pipeline_runs WHERE meeting_id = ? ORDER BY started_at DESC",
            (meeting_id,),
        )
        return [self._row_to_run(r, cur.description) for r in await cur.fetchall()]

    # ------------------------------------------------------------------
    # ExecutionRecord persistence
    # ------------------------------------------------------------------

    async def save_execution(self, record: ExecutionRecord) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO execution_records
               (record_id, meeting_id, run_id,
                intent_id, intent_type, source_speaker, source_text,
                source_timestamp, confidence,
                target, rule_id, payload,
                risk_level, risk_reason, approved_by, approved_at, expires_at,
                status, executed_at, execution_result,
                rollback_hint, rolled_back_at, rollback_result,
                created_at)
               VALUES (?, ?, ?,  ?, ?, ?, ?, ?, ?,  ?, ?, ?,  ?, ?, ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?)""",
            (
                record.record_id, record.meeting_id, record.run_id,
                record.intent_id, record.intent_type, record.source_speaker,
                record.source_text, record.source_timestamp, record.confidence,
                record.target, record.rule_id, json.dumps(record.payload),
                record.risk_level.value, record.risk_reason,
                record.approved_by,
                record.approved_at.isoformat() if record.approved_at else None,
                record.expires_at.isoformat() if record.expires_at else None,
                record.status.value,
                record.executed_at.isoformat() if record.executed_at else None,
                json.dumps(record.execution_result) if record.execution_result else None,
                record.rollback_hint,
                record.rolled_back_at.isoformat() if record.rolled_back_at else None,
                json.dumps(record.rollback_result) if record.rollback_result else None,
                record.created_at.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_execution(self, record_id: str) -> Optional[ExecutionRecord]:
        cur = await self._db.execute(
            "SELECT * FROM execution_records WHERE record_id = ?", (record_id,)
        )
        row = await cur.fetchone()
        return self._row_to_exec(row, cur.description) if row else None

    async def get_executions_by_meeting(self, meeting_id: str) -> list[ExecutionRecord]:
        cur = await self._db.execute(
            "SELECT * FROM execution_records WHERE meeting_id = ? ORDER BY created_at",
            (meeting_id,),
        )
        return [self._row_to_exec(r, cur.description) for r in await cur.fetchall()]

    async def get_executions_by_status(self, status: ExecutionStatus) -> list[ExecutionRecord]:
        cur = await self._db.execute(
            "SELECT * FROM execution_records WHERE status = ? ORDER BY created_at",
            (status.value,),
        )
        return [self._row_to_exec(r, cur.description) for r in await cur.fetchall()]

    async def get_pending_approvals(self) -> list[ExecutionRecord]:
        return await self.get_executions_by_status(ExecutionStatus.AWAITING_APPROVAL)

    async def get_overdue_approvals(self, now: Optional[datetime] = None) -> list[ExecutionRecord]:
        """Get AWAITING_APPROVAL records whose expires_at has passed."""
        now = now or datetime.now(timezone.utc)
        cur = await self._db.execute(
            """SELECT * FROM execution_records
               WHERE status = ? AND expires_at IS NOT NULL AND expires_at < ?
               ORDER BY expires_at""",
            (ExecutionStatus.AWAITING_APPROVAL.value, now.isoformat()),
        )
        return [self._row_to_exec(r, cur.description) for r in await cur.fetchall()]

    async def update_execution_status(
        self, record_id: str, status: ExecutionStatus, **kwargs,
    ) -> Optional[ExecutionRecord]:
        _ALLOWED_COLS = {
            "executed_at", "approved_by", "approved_at",
            "execution_result", "rolled_back_at", "rollback_result",
        }
        sets = ["status = ?"]
        params: list = [status.value]

        for col in _ALLOWED_COLS:
            if col in kwargs:
                val = kwargs[col]
                if isinstance(val, datetime):
                    val = val.isoformat()
                elif isinstance(val, dict):
                    val = json.dumps(val)
                sets.append(f"{col} = ?")
                params.append(val)

        params.append(record_id)
        await self._db.execute(
            f"UPDATE execution_records SET {', '.join(sets)} WHERE record_id = ?",
            params,
        )
        await self._db.commit()
        return await self.get_execution(record_id)

    # ------------------------------------------------------------------
    # Row → Model helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row, description) -> dict:
        return {col[0]: row[i] for i, col in enumerate(description)}

    @classmethod
    def _row_to_run(cls, row, description) -> PipelineRun:
        d = cls._row_to_dict(row, description)
        return PipelineRun(
            run_id=d["run_id"], meeting_id=d["meeting_id"],
            status=PipelineRunStatus(d["status"]),
            input_type=d["input_type"], input_length=d["input_length"],
            intent_count=d["intent_count"], route_count=d["route_count"],
            error=d["error"],
            started_at=datetime.fromisoformat(d["started_at"]),
            completed_at=datetime.fromisoformat(d["completed_at"]) if d["completed_at"] else None,
            duration_ms=d["duration_ms"],
        )

    @classmethod
    def _row_to_exec(cls, row, description) -> ExecutionRecord:
        d = cls._row_to_dict(row, description)
        return ExecutionRecord(
            record_id=d["record_id"], meeting_id=d["meeting_id"], run_id=d["run_id"],
            intent_id=d["intent_id"], intent_type=d["intent_type"],
            source_speaker=d["source_speaker"], source_text=d["source_text"],
            source_timestamp=d["source_timestamp"], confidence=d["confidence"],
            target=d["target"], rule_id=d["rule_id"],
            payload=json.loads(d["payload"]) if d["payload"] else {},
            risk_level=RiskLevel(d["risk_level"]),
            risk_reason=d["risk_reason"] or "",
            approved_by=d["approved_by"],
            approved_at=datetime.fromisoformat(d["approved_at"]) if d["approved_at"] else None,
            expires_at=datetime.fromisoformat(d["expires_at"]) if d["expires_at"] else None,
            status=ExecutionStatus(d["status"]),
            executed_at=datetime.fromisoformat(d["executed_at"]) if d["executed_at"] else None,
            execution_result=json.loads(d["execution_result"]) if d["execution_result"] else None,
            rollback_hint=d["rollback_hint"] or "",
            rolled_back_at=datetime.fromisoformat(d["rolled_back_at"]) if d["rolled_back_at"] else None,
            rollback_result=json.loads(d["rollback_result"]) if d["rollback_result"] else None,
            created_at=datetime.fromisoformat(d["created_at"]),
        )
