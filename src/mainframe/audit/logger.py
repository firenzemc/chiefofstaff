"""
In-memory audit logger for pipeline runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import PipelineRun, PipelineRunStatus


class AuditLogger:
    """
    Records pipeline execution lifecycle.

    Storage is in-memory (list); swap for a DB adapter post-MVP.
    """

    def __init__(self) -> None:
        self.runs: list[PipelineRun] = []

    async def start_run(
        self,
        meeting_id: str,
        input_type: str,
        input_length: int,
    ) -> PipelineRun:
        """Create and store a new pipeline run record."""
        run = PipelineRun(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            meeting_id=meeting_id,
            status=PipelineRunStatus.STARTED,
            input_type=input_type,
            input_length=input_length,
        )
        self.runs.append(run)
        return run

    async def update_status(
        self,
        run_id: str,
        status: PipelineRunStatus,
    ) -> Optional[PipelineRun]:
        """Transition a run to a new status."""
        run = self._find(run_id)
        if run is None:
            return None
        run.status = status
        return run

    async def complete_run(
        self,
        run_id: str,
        intent_count: int,
        route_count: int,
    ) -> Optional[PipelineRun]:
        """Mark a run as completed with result counts."""
        run = self._find(run_id)
        if run is None:
            return None
        run.status = PipelineRunStatus.COMPLETED
        run.intent_count = intent_count
        run.route_count = route_count
        run.completed_at = datetime.now(timezone.utc)
        run.duration_ms = int(
            (run.completed_at - run.started_at).total_seconds() * 1000
        )
        return run

    async def fail_run(self, run_id: str, error: str) -> Optional[PipelineRun]:
        """Mark a run as failed."""
        run = self._find(run_id)
        if run is None:
            return None
        run.status = PipelineRunStatus.FAILED
        run.error = error
        run.completed_at = datetime.now(timezone.utc)
        run.duration_ms = int(
            (run.completed_at - run.started_at).total_seconds() * 1000
        )
        return run

    async def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """Retrieve a single run by ID."""
        return self._find(run_id)

    async def get_by_meeting(self, meeting_id: str) -> list[PipelineRun]:
        """Retrieve all runs for a given meeting."""
        return [r for r in self.runs if r.meeting_id == meeting_id]

    def _find(self, run_id: str) -> Optional[PipelineRun]:
        for run in self.runs:
            if run.run_id == run_id:
                return run
        return None
