"""Tests for end-to-end batch pipeline."""

import pytest
from mainframe.understanding.batch.pipeline import BatchPipeline
from mainframe.understanding.batch.models import MeetingAnalysis


class TestBatchPipeline:
    @pytest.mark.asyncio
    async def test_run_with_text(self, sample_transcript_text):
        pipeline = BatchPipeline()
        result = await pipeline.run(sample_transcript_text, meeting_id="m1")

        assert isinstance(result, MeetingAnalysis)
        assert result.meeting_id == "m1"
        assert len(result.intents) > 0
        assert result.summary  # non-empty

    @pytest.mark.asyncio
    async def test_run_stores_feedback(self, sample_transcript_text):
        pipeline = BatchPipeline()
        await pipeline.run(sample_transcript_text, meeting_id="m2")

        assert len(pipeline.feedback_collector.storage) == 1
        stored = pipeline.feedback_collector.storage[0]
        assert stored["meeting_id"] == "m2"

    @pytest.mark.asyncio
    async def test_run_generates_meeting_id(self, sample_transcript_text):
        pipeline = BatchPipeline()
        result = await pipeline.run(sample_transcript_text)
        assert result.meeting_id.startswith("meeting-")

    @pytest.mark.asyncio
    async def test_pipeline_components_exist(self):
        pipeline = BatchPipeline()
        assert hasattr(pipeline, "transcriber")
        assert hasattr(pipeline, "extractor")
        assert hasattr(pipeline, "feedback_collector")
