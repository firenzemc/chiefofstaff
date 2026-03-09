"""
Routing engine — matches intents to rules and builds a RoutingPlan.
"""

from __future__ import annotations

from typing import Optional

from ..understanding.batch.models import Intent, MeetingAnalysis
from .default_rules import DEFAULT_RULES
from .models import RouteResult, RouteRule, RouteTarget, RoutingPlan


class RoutingEngine:
    """
    Stateless rule-based routing engine.

    For each intent in a ``MeetingAnalysis``, the engine finds the highest-
    priority rule whose ``intent_type`` matches.  If no rule matches the
    intent is added to the *unrouted* list.
    """

    def __init__(self, rules: Optional[list[RouteRule]] = None):
        # Sort by priority descending so the first match wins.
        self._rules = sorted(
            rules or DEFAULT_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, analysis: MeetingAnalysis) -> RoutingPlan:
        """Build a ``RoutingPlan`` for every intent in *analysis*."""
        routes: list[RouteResult] = []
        unrouted: list[str] = []

        for intent in analysis.intents:
            rule = self._match(intent)
            if rule is None:
                unrouted.append(intent.id)
                continue
            routes.append(
                RouteResult(
                    intent_id=intent.id,
                    intent_type=intent.type.value,
                    target=rule.target,
                    rule_id=rule.id,
                    payload=self._build_payload(intent, rule.target),
                )
            )

        return RoutingPlan(
            meeting_id=analysis.meeting_id,
            routes=routes,
            unrouted=unrouted,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _match(self, intent: Intent) -> Optional[RouteRule]:
        """Return the first (highest-priority) matching rule, or ``None``."""
        for rule in self._rules:
            if rule.intent_type == intent.type.value:
                return rule
        return None

    @staticmethod
    def _build_payload(intent: Intent, target: RouteTarget) -> dict:
        """Build a connector-specific payload dict."""
        base = {
            "content": intent.content,
            "speaker": intent.speaker,
            "confidence": intent.confidence,
        }

        if target == RouteTarget.TASK_TRACKER:
            base["title"] = intent.content[:120]
            base["assignee"] = intent.speaker
        elif target == RouteTarget.DOCUMENT:
            base["section"] = "Decisions"
        elif target == RouteTarget.IM_MESSAGE:
            base["text"] = intent.content
        elif target == RouteTarget.AGENT:
            base["query"] = intent.content

        return base
