"""
Request / response schemas for the REST API.
"""

from typing import List, Optional

from pydantic import BaseModel

from ..understanding.batch.models import ActionItem, Intent
from ..router.models import RouteResult


class AnalyzeRequest(BaseModel):
    """POST /analyze request body."""

    text: str
    meeting_id: Optional[str] = None
    language: str = "auto"


class AnalyzeResponse(BaseModel):
    """POST /analyze response body."""

    meeting_id: str
    summary: str
    intents: List[Intent]
    decisions: List[str]
    action_items: List[ActionItem]
    open_questions: List[str]
    commitments: List[str]
    routes: List[RouteResult]
    run_id: str
