"""
Data models for the routing engine.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RouteTarget(str, Enum):
    """Where an intent gets routed."""

    TASK_TRACKER = "task_tracker"
    IM_MESSAGE = "im_message"
    DOCUMENT = "document"
    AGENT = "agent"
    NONE = "none"


class RouteRule(BaseModel):
    """A single routing rule."""

    id: str
    intent_type: str  # IntentType value (e.g. "decision")
    target: RouteTarget
    priority: int = 0
    condition: Optional[str] = None  # Reserved for future use


class RouteResult(BaseModel):
    """Result of routing a single intent."""

    intent_id: str
    intent_type: str
    target: RouteTarget
    rule_id: str
    payload: dict = Field(default_factory=dict)


class RoutingPlan(BaseModel):
    """Complete routing plan for a meeting analysis."""

    meeting_id: str
    routes: List[RouteResult] = Field(default_factory=list)
    unrouted: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
