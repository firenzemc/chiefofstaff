"""Tests for Pydantic data models."""

import pytest
from mainframe.understanding.batch.models import (
    ActionItem, Entity, Intent, IntentType, MeetingAnalysis, Transcript, TranscriptSegment,
)


class TestTranscriptSegment:
    def test_creation(self):
        seg = TranscriptSegment(speaker="Alice", text="Hello", start_time=0.0, end_time=1.0)
        assert seg.speaker == "Alice"
        assert seg.text == "Hello"

    def test_transcript(self, sample_segments):
        t = Transcript(segments=sample_segments, language="en", duration=15.0)
        assert len(t.segments) == 5
        assert t.language == "en"


class TestIntentType:
    def test_all_values(self):
        assert IntentType.DECISION == "decision"
        assert IntentType.ACTION_ITEM == "action_item"
        assert IntentType.OPEN_QUESTION == "open_question"
        assert IntentType.COMMITMENT == "commitment"
        assert IntentType.INFO == "info"

    def test_from_string(self):
        assert IntentType("decision") == IntentType.DECISION


class TestIntent:
    def test_creation(self):
        intent = Intent(
            id="i1", type=IntentType.DECISION, content="Launch",
            confidence=0.95, speaker="Alice", timestamp=1.0,
        )
        assert intent.confidence == 0.95
        assert intent.entities == []

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            Intent(id="i1", type=IntentType.INFO, content="x", confidence=1.5, speaker="A", timestamp=0)

    def test_with_entities(self):
        intent = Intent(
            id="i1", type=IntentType.ACTION_ITEM, content="Do X",
            confidence=0.9, speaker="Bob", timestamp=2.0,
            entities=[Entity(type="person", value="Bob")],
        )
        assert len(intent.entities) == 1
        assert intent.entities[0].value == "Bob"


class TestMeetingAnalysis:
    def test_creation(self, sample_analysis):
        assert sample_analysis.meeting_id == "meeting-test-001"
        assert len(sample_analysis.intents) == 5
        assert len(sample_analysis.decisions) == 1

    def test_defaults(self):
        a = MeetingAnalysis(meeting_id="m1", summary="s", intents=[])
        assert a.decisions == []
        assert a.action_items == []
        assert a.open_questions == []
        assert a.commitments == []
        assert a.created_at is not None


class TestActionItem:
    def test_minimal(self):
        ai = ActionItem(what="Do the thing")
        assert ai.who is None
        assert ai.when is None

    def test_full(self):
        ai = ActionItem(who="Bob", what="Write docs", when="Friday")
        assert ai.who == "Bob"
