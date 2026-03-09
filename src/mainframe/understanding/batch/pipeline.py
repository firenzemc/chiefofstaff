"""
Batch understanding pipeline.

End-to-end pipeline: text transcript → intent extraction → routing → feedback.
"""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from .transcription import TranscriptionService
from .intent_extractor import IntentExtractor
from .models import MeetingAnalysis, Transcript
from ...feedback.collector import FeedbackCollector


class BatchPipeline:
    """
    Batch processing pipeline for meeting understanding.

    MVP flow:  Text → Transcript → Intent Extraction → Feedback
    """

    def __init__(
        self,
        llm_client: Optional[AsyncOpenAI] = None,
        llm_model: str = "gpt-4o-mini",
        feedback_collector: Optional[FeedbackCollector] = None,
    ):
        self.transcriber = TranscriptionService()
        self.extractor = IntentExtractor(client=llm_client, model=llm_model)
        self.feedback_collector = feedback_collector or FeedbackCollector()

    async def run(
        self,
        text: str,
        meeting_id: str = "",
    ) -> MeetingAnalysis:
        """
        Run the batch pipeline on a text transcript.

        Args:
            text: Raw text transcript ("Speaker: content" lines).
            meeting_id: Optional client-provided meeting ID.

        Returns:
            MeetingAnalysis with extracted intents.
        """
        transcript = await self.transcriber.transcribe_text(text)
        analysis = await self.extractor.extract(transcript, meeting_id=meeting_id)
        await self._store_analysis(analysis)
        return analysis

    async def _store_analysis(self, analysis: MeetingAnalysis) -> None:
        """Store analysis in feedback collector."""
        await self.feedback_collector.submit({
            "meeting_id": analysis.meeting_id,
            "summary": analysis.summary,
            "intent_count": len(analysis.intents),
            "decisions": analysis.decisions,
            "action_items": [
                {"who": a.who, "what": a.what, "when": a.when}
                for a in analysis.action_items
            ],
            "open_questions": analysis.open_questions,
            "commitments": analysis.commitments,
        })
