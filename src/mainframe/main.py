"""
Mainframe — FastAPI application entry point.

Run with:  python -m mainframe.main
Or:        uvicorn mainframe.main:app --reload
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI

from .api.schemas import AnalyzeRequest, AnalyzeResponse
from .audit.logger import AuditLogger
from .audit.models import PipelineRunStatus
from .config import settings
from .connectors.mock import MockConnector
from .feedback.collector import FeedbackCollector
from .router.engine import RoutingEngine
from .understanding.batch.intent_extractor import IntentExtractor
from .understanding.batch.transcription import TranscriptionService


# ---------------------------------------------------------------------------
# Shared singletons (created at startup)
# ---------------------------------------------------------------------------

_extractor: Optional[IntentExtractor] = None
_router: Optional[RoutingEngine] = None
_audit: Optional[AuditLogger] = None
_feedback: Optional[FeedbackCollector] = None
_connector: Optional[MockConnector] = None
_transcriber: Optional[TranscriptionService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _extractor, _router, _audit, _feedback, _connector, _transcriber

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
    _feedback = FeedbackCollector()
    _connector = MockConnector()
    _transcriber = TranscriptionService()

    yield  # app is running

    # Shutdown: nothing to clean up for in-memory stores


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mainframe",
    description="The chief of staff for your agents.",
    version="0.1.0",
    lifespan=lifespan,
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

    # 1. Audit: start
    run = await _audit.start_run(
        meeting_id=meeting_id,
        input_type="text",
        input_length=len(request.text),
    )

    try:
        # 2. Transcribe text → Transcript
        await _audit.update_status(run.run_id, PipelineRunStatus.EXTRACTING)
        transcript = await _transcriber.transcribe_text(request.text)

        # 3. Extract intents
        analysis = await _extractor.extract(transcript, meeting_id=meeting_id)

        # 4. Route
        await _audit.update_status(run.run_id, PipelineRunStatus.ROUTING)
        plan = _router.route(analysis)

        # 5. Execute routes via mock connector
        for route in plan.routes:
            await _connector.execute(route)

        # 6. Store in feedback collector
        await _feedback.submit({
            "meeting_id": meeting_id,
            "summary": analysis.summary,
            "intent_count": len(analysis.intents),
        })

        # 7. Audit: complete
        await _audit.complete_run(
            run.run_id,
            intent_count=len(analysis.intents),
            route_count=len(plan.routes),
        )

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
        await _audit.fail_run(run.run_id, str(exc))
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")


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
