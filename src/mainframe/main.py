"""
Mainframe — FastAPI application entry point.

Run with:  python -m mainframe.main
Or:        uvicorn mainframe.main:app --reload
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI

from .api.schemas import AnalyzeRequest, AnalyzeResponse
from .audit.logger import AuditLogger
from .audit.models import (
    ExecutionRecord,
    ExecutionStatus,
    PipelineRunStatus,
    RiskLevel,
)
from .audit.risk import RiskAssessor
from .audit.store import AuditStore
from .config import settings
from .connectors.mock import MockConnector
from .feedback.collector import FeedbackCollector
from .memory.matcher import CommitmentMatcher
from .memory.models import Commitment, CommitmentStatus
from .memory.store import MemoryStore
from .router.engine import RoutingEngine
from .router.models import RouteResult
from .understanding.batch.intent_extractor import IntentExtractor
from .understanding.batch.models import Intent, IntentType
from .understanding.batch.transcription import TranscriptionService


# ---------------------------------------------------------------------------
# Shared singletons (created at startup)
# ---------------------------------------------------------------------------

_extractor: Optional[IntentExtractor] = None
_router: Optional[RoutingEngine] = None
_audit: Optional[AuditLogger] = None
_audit_store: Optional[AuditStore] = None
_risk_assessor: Optional[RiskAssessor] = None
_feedback: Optional[FeedbackCollector] = None
_connector: Optional[MockConnector] = None
_transcriber: Optional[TranscriptionService] = None
_memory_store: Optional[MemoryStore] = None
_commitment_matcher: Optional[CommitmentMatcher] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _extractor, _router, _audit, _audit_store, _risk_assessor
    global _feedback, _connector, _transcriber, _memory_store, _commitment_matcher

    # LLM client — only if api_key is configured
    llm_client = None
    if settings.llm_api_key:
        llm_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    _extractor = IntentExtractor(client=llm_client, model=settings.llm_model)
    _router = RoutingEngine()
    _audit = AuditLogger()
    _risk_assessor = RiskAssessor()
    _feedback = FeedbackCollector()
    _connector = MockConnector()
    _transcriber = TranscriptionService()
    _commitment_matcher = CommitmentMatcher()

    # Persistent stores
    _audit_store = AuditStore(settings.audit_db_path)
    await _audit_store.init()

    _memory_store = MemoryStore(settings.memory_db_path)
    await _memory_store.init()

    yield

    if _audit_store:
        await _audit_store.close()
    if _memory_store:
        await _memory_store.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mainframe",
    description="The chief of staff for your agents.",
    version="0.2.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _intent_by_id(intents: list[Intent], intent_id: str) -> Optional[Intent]:
    for i in intents:
        if i.id == intent_id:
            return i
    return None


async def _process_memory(
    intent: Intent,
    meeting_id: str,
) -> None:
    """Update memory store based on intent type."""
    # Track commitments / action items
    if intent.type in (IntentType.COMMITMENT, IntentType.ACTION_ITEM):
        open_commitments = await _memory_store.get_open_commitments(owner=intent.speaker)
        matched = _commitment_matcher.match(intent, open_commitments)

        if matched:
            # Re-mention: bump count and meeting list
            await _memory_store.record_mention(matched.commitment_id, meeting_id)
        else:
            # New commitment
            commitment = Commitment(
                commitment_id=f"c-{uuid.uuid4().hex[:8]}",
                content=intent.content,
                owner=intent.speaker,
                source_meeting_id=meeting_id,
                source_intent_id=intent.id,
                source_text=intent.content,
                mention_meetings=[meeting_id],
            )
            await _memory_store.save_commitment(commitment)

    # Record entity facts
    for entity in intent.entities:
        await _memory_store.add_entity_fact(
            entity_type=entity.type,
            entity_value=entity.value,
            meeting_id=meeting_id,
            fact=intent.content,
            speaker=intent.speaker,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """Analyze a meeting transcript and return structured intents + routes."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    meeting_id = request.meeting_id or f"meeting-{uuid.uuid4().hex[:8]}"

    # 1. Audit: start run
    run = await _audit.start_run(
        meeting_id=meeting_id,
        input_type="text",
        input_length=len(request.text),
    )
    await _audit_store.save_run(run)

    try:
        # 2. Transcribe text → Transcript
        await _audit.update_status(run.run_id, PipelineRunStatus.EXTRACTING)
        transcript = await _transcriber.transcribe_text(request.text)

        # 3. Extract intents
        analysis = await _extractor.extract(transcript, meeting_id=meeting_id)

        # 4. Route
        await _audit.update_status(run.run_id, PipelineRunStatus.ROUTING)
        plan = _router.route(analysis)

        # 5. Risk-assess, record, and execute each route
        for route in plan.routes:
            intent = _intent_by_id(analysis.intents, route.intent_id)
            if intent is None:
                continue

            # Risk assessment
            risk_level, risk_reason = _risk_assessor.assess(route, intent)

            # Determine initial status based on risk
            if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                initial_status = ExecutionStatus.AWAITING_APPROVAL
            else:
                initial_status = ExecutionStatus.PENDING

            # Build execution record
            rollback_hint = MockConnector.build_rollback_hint(route)
            exec_record = ExecutionRecord(
                record_id=f"exec-{uuid.uuid4().hex[:8]}",
                meeting_id=meeting_id,
                run_id=run.run_id,
                intent_id=route.intent_id,
                intent_type=route.intent_type,
                source_speaker=route.source_speaker,
                source_text=route.source_text,
                source_timestamp=route.source_timestamp,
                confidence=route.confidence,
                target=route.target.value,
                rule_id=route.rule_id,
                payload=route.payload,
                risk_level=risk_level,
                risk_reason=risk_reason,
                status=initial_status,
                rollback_hint=rollback_hint,
            )

            # Execute if auto-approved (LOW / MEDIUM)
            if initial_status == ExecutionStatus.PENDING:
                result = await _connector.execute(route)
                exec_record.status = ExecutionStatus.EXECUTED
                exec_record.executed_at = datetime.now(timezone.utc)
                exec_record.execution_result = result

            await _audit_store.save_execution(exec_record)

            # 6. Memory update for each intent
            await _process_memory(intent, meeting_id)

        # 7. Store in feedback collector
        await _feedback.submit({
            "meeting_id": meeting_id,
            "summary": analysis.summary,
            "intent_count": len(analysis.intents),
        })

        # 8. Audit: complete run
        completed = await _audit.complete_run(
            run.run_id,
            intent_count=len(analysis.intents),
            route_count=len(plan.routes),
        )
        await _audit_store.save_run(completed)

        return AnalyzeResponse(
            meeting_id=meeting_id,
            summary=analysis.summary,
            intents=analysis.intents,
            decisions=analysis.decisions,
            action_items=analysis.action_items,
            open_questions=analysis.open_questions,
            commitments=analysis.commitments,
            routes=plan.routes,
            run_id=run.run_id,
        )

    except ValueError as exc:
        await _audit.fail_run(run.run_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        failed = await _audit.fail_run(run.run_id, str(exc))
        if failed:
            await _audit_store.save_run(failed)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")


# ---------------------------------------------------------------------------
# Execution approval endpoints
# ---------------------------------------------------------------------------

@app.get("/executions/{meeting_id}")
async def get_executions(meeting_id: str):
    """Get all execution records for a meeting."""
    records = await _audit_store.get_executions_by_meeting(meeting_id)
    return {"meeting_id": meeting_id, "executions": [r.model_dump() for r in records]}


@app.get("/approvals/pending")
async def get_pending_approvals():
    """Get all executions awaiting human approval."""
    records = await _audit_store.get_pending_approvals()
    return {"pending": [r.model_dump() for r in records]}


@app.post("/approvals/{record_id}/approve")
async def approve_execution(record_id: str, approved_by: str = "human"):
    """Approve a pending execution and execute it."""
    record = await _audit_store.get_execution(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Execution record not found")
    if record.status != ExecutionStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400, detail=f"Cannot approve: status is {record.status.value}"
        )

    route = RouteResult(
        intent_id=record.intent_id,
        intent_type=record.intent_type,
        target=record.target,
        rule_id=record.rule_id,
        payload=record.payload,
        source_speaker=record.source_speaker,
        source_text=record.source_text,
        source_timestamp=record.source_timestamp,
        confidence=record.confidence,
    )
    result = await _connector.execute(route)

    updated = await _audit_store.update_execution_status(
        record_id,
        ExecutionStatus.EXECUTED,
        approved_by=approved_by,
        approved_at=datetime.now(timezone.utc),
        executed_at=datetime.now(timezone.utc),
        execution_result=result,
    )
    return {"status": "approved_and_executed", "record": updated.model_dump()}


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------

@app.get("/commitments")
async def list_commitments(owner: Optional[str] = None, repeated: bool = False):
    """List open commitments, optionally filtered by owner or repeated only."""
    if repeated:
        items = await _memory_store.get_repeated_commitments(min_mentions=2)
    else:
        items = await _memory_store.get_open_commitments(owner=owner)
    return {"commitments": [c.model_dump() for c in items]}


@app.post("/commitments/{commitment_id}/close")
async def close_commitment(
    commitment_id: str,
    closed_by: str = "human",
    evidence: Optional[str] = None,
):
    """Mark a commitment as completed."""
    updated = await _memory_store.update_commitment_status(
        commitment_id,
        CommitmentStatus.COMPLETED,
        closed_at=datetime.now(timezone.utc),
        closed_by=closed_by,
        closed_evidence=evidence,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return {"status": "closed", "commitment": updated.model_dump()}


@app.get("/memory/entity")
async def get_entity_memory(entity_type: str, entity_value: str):
    """Get accumulated facts about a named entity."""
    mem = await _memory_store.get_entity_memory(entity_type, entity_value)
    if mem is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return mem.model_dump()


@app.get("/memory/search")
async def search_entity_memory(q: str):
    """Search entity memory by keyword."""
    results = await _memory_store.search_entities(q)
    return {"results": results}


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "mainframe.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
