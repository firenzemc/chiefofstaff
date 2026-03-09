"""Tests for IntentExtractor."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mainframe.understanding.batch.intent_extractor import IntentExtractor
from mainframe.understanding.batch.models import (
    IntentType, MeetingAnalysis, Transcript, TranscriptSegment,
)


class TestIntentExtractorMock:
    """Tests using the mock (no LLM) path."""

    def test_init_mock_mode(self):
        ext = IntentExtractor()
        assert ext.client is None
        assert ext.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_extract_mock(self, sample_transcript):
        ext = IntentExtractor()
        result = await ext.extract(sample_transcript, meeting_id="m1")

        assert isinstance(result, MeetingAnalysis)
        assert result.meeting_id == "m1"
        assert len(result.intents) == 5
        assert result.summary  # non-empty

    @pytest.mark.asyncio
    async def test_mock_classifies_decision(self):
        t = Transcript(segments=[
            TranscriptSegment(speaker="A", text="We decided to go.", start_time=0, end_time=1),
        ], language="en", duration=1.0)

        ext = IntentExtractor()
        result = await ext.extract(t)
        assert result.intents[0].type == IntentType.DECISION

    @pytest.mark.asyncio
    async def test_mock_classifies_question(self):
        t = Transcript(segments=[
            TranscriptSegment(speaker="A", text="What about the deadline?", start_time=0, end_time=1),
        ], language="en", duration=1.0)

        ext = IntentExtractor()
        result = await ext.extract(t)
        assert result.intents[0].type == IntentType.OPEN_QUESTION

    @pytest.mark.asyncio
    async def test_mock_classifies_commitment(self):
        t = Transcript(segments=[
            TranscriptSegment(speaker="A", text="I'll commit to that.", start_time=0, end_time=1),
        ], language="en", duration=1.0)

        ext = IntentExtractor()
        result = await ext.extract(t)
        assert result.intents[0].type == IntentType.COMMITMENT

    @pytest.mark.asyncio
    async def test_empty_transcript_raises(self):
        t = Transcript(segments=[], language="en", duration=0.0)
        ext = IntentExtractor()
        with pytest.raises(ValueError, match="empty transcript"):
            await ext.extract(t)

    @pytest.mark.asyncio
    async def test_meeting_id_generated_if_empty(self, sample_transcript):
        ext = IntentExtractor()
        result = await ext.extract(sample_transcript)
        assert result.meeting_id.startswith("meeting-")


class TestIntentExtractorLLM:
    """Tests for the LLM path with mocked openai client."""

    @pytest.mark.asyncio
    async def test_extract_with_llm(self, sample_transcript, sample_llm_response):
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(sample_llm_response)
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        ext = IntentExtractor(client=mock_client, model="test-model")
        result = await ext.extract(sample_transcript, meeting_id="m2")

        assert result.meeting_id == "m2"
        assert len(result.intents) == 5
        assert result.intents[0].type == IntentType.DECISION
        assert result.intents[1].type == IntentType.ACTION_ITEM
        assert result.decisions == ["Launch next week"]
        assert len(result.action_items) == 1
        assert result.action_items[0].who == "Bob"

        # Verify LLM was called with correct params
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["temperature"] == 0.1

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back(self, sample_transcript):
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "not json at all"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        ext = IntentExtractor(client=mock_client)
        # Should raise JSONDecodeError or similar
        with pytest.raises(Exception):
            await ext.extract(sample_transcript)

    @pytest.mark.asyncio
    async def test_empty_llm_response(self, sample_transcript):
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "{}"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        ext = IntentExtractor(client=mock_client)
        result = await ext.extract(sample_transcript, meeting_id="m3")

        assert result.meeting_id == "m3"
        assert result.intents == []
        assert result.summary == ""


class TestParseResponse:
    """Tests for _parse_response directly."""

    def test_unknown_intent_type_defaults_to_info(self):
        ext = IntentExtractor()
        data = {
            "intents": [{"type": "unknown_type", "content": "test", "speaker": "A", "timestamp": 0}],
            "summary": "s",
        }
        result = ext._parse_response(data, "m1")
        assert result.intents[0].type == IntentType.INFO

    def test_missing_fields_use_defaults(self):
        ext = IntentExtractor()
        data = {"intents": [{}], "summary": "s"}
        result = ext._parse_response(data, "m1")
        assert result.intents[0].speaker == "Unknown"
        assert result.intents[0].confidence == 0.5
