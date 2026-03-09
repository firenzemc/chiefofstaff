"""
Default routing rules for the MVP.

Maps each IntentType to a RouteTarget.
"""

from .models import RouteRule, RouteTarget


DEFAULT_RULES: list[RouteRule] = [
    RouteRule(
        id="rule-decision-doc",
        intent_type="decision",
        target=RouteTarget.DOCUMENT,
        priority=10,
    ),
    RouteRule(
        id="rule-action-task",
        intent_type="action_item",
        target=RouteTarget.TASK_TRACKER,
        priority=10,
    ),
    RouteRule(
        id="rule-question-agent",
        intent_type="open_question",
        target=RouteTarget.AGENT,
        priority=5,
    ),
    RouteRule(
        id="rule-commitment-task",
        intent_type="commitment",
        target=RouteTarget.TASK_TRACKER,
        priority=5,
    ),
    RouteRule(
        id="rule-info-none",
        intent_type="info",
        target=RouteTarget.NONE,
        priority=0,
    ),
]
