"""Tests for the routing engine."""

import pytest

from mainframe.router.engine import RoutingEngine
from mainframe.router.models import RouteRule, RouteTarget, RoutingPlan
from mainframe.router.default_rules import DEFAULT_RULES
from mainframe.understanding.batch.models import IntentType


class TestDefaultRules:
    def test_all_intent_types_covered(self):
        rule_types = {r.intent_type for r in DEFAULT_RULES}
        for it in IntentType:
            assert it.value in rule_types, f"{it.value} has no default rule"

    def test_decision_goes_to_document(self):
        r = next(r for r in DEFAULT_RULES if r.intent_type == "decision")
        assert r.target == RouteTarget.DOCUMENT

    def test_action_item_goes_to_task(self):
        r = next(r for r in DEFAULT_RULES if r.intent_type == "action_item")
        assert r.target == RouteTarget.TASK_TRACKER

    def test_open_question_goes_to_agent(self):
        r = next(r for r in DEFAULT_RULES if r.intent_type == "open_question")
        assert r.target == RouteTarget.AGENT

    def test_info_goes_to_none(self):
        r = next(r for r in DEFAULT_RULES if r.intent_type == "info")
        assert r.target == RouteTarget.NONE


class TestRoutingEngine:
    def test_init_with_defaults(self):
        engine = RoutingEngine()
        assert len(engine._rules) == len(DEFAULT_RULES)

    def test_init_with_custom_rules(self, custom_rules):
        engine = RoutingEngine(rules=custom_rules)
        assert len(engine._rules) == 2

    def test_route_all_intents(self, sample_analysis):
        engine = RoutingEngine()
        plan = engine.route(sample_analysis)

        assert isinstance(plan, RoutingPlan)
        assert plan.meeting_id == sample_analysis.meeting_id
        assert len(plan.routes) == 5
        assert plan.unrouted == []

    def test_route_targets_correct(self, sample_analysis):
        engine = RoutingEngine()
        plan = engine.route(sample_analysis)

        targets = {r.intent_id: r.target for r in plan.routes}
        assert targets["intent-1"] == RouteTarget.DOCUMENT       # decision
        assert targets["intent-2"] == RouteTarget.TASK_TRACKER    # action_item
        assert targets["intent-3"] == RouteTarget.AGENT           # open_question
        assert targets["intent-4"] == RouteTarget.TASK_TRACKER    # commitment
        assert targets["intent-5"] == RouteTarget.NONE            # info

    def test_unmatched_intents(self, sample_analysis):
        # Rules that only match decisions — everything else is unrouted
        rules = [RouteRule(id="r1", intent_type="decision", target=RouteTarget.DOCUMENT)]
        engine = RoutingEngine(rules=rules)
        plan = engine.route(sample_analysis)

        assert len(plan.routes) == 1
        assert len(plan.unrouted) == 4

    def test_payload_has_content(self, sample_analysis):
        engine = RoutingEngine()
        plan = engine.route(sample_analysis)

        for route in plan.routes:
            assert "content" in route.payload
            assert "speaker" in route.payload

    def test_task_payload_has_title(self, sample_analysis):
        engine = RoutingEngine()
        plan = engine.route(sample_analysis)

        action_route = next(r for r in plan.routes if r.intent_id == "intent-2")
        assert "title" in action_route.payload
        assert "assignee" in action_route.payload

    def test_empty_analysis(self):
        from mainframe.understanding.batch.models import MeetingAnalysis
        analysis = MeetingAnalysis(meeting_id="m1", summary="empty", intents=[])
        engine = RoutingEngine()
        plan = engine.route(analysis)
        assert plan.routes == []
        assert plan.unrouted == []

    def test_rules_sorted_by_priority(self):
        rules = [
            RouteRule(id="low", intent_type="info", target=RouteTarget.NONE, priority=1),
            RouteRule(id="high", intent_type="info", target=RouteTarget.IM_MESSAGE, priority=10),
        ]
        engine = RoutingEngine(rules=rules)
        # High priority should come first
        assert engine._rules[0].id == "high"
