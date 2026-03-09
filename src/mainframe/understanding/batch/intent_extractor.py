"""
Intent extraction service using LLM.

Uses the OpenAI SDK (compatible with any OpenAI-API-compatible provider).
When no client is provided, falls back to a keyword-based mock for testing.
"""

import json
import uuid
from typing import Optional

from openai import AsyncOpenAI

from .models import (
    Intent,
    IntentType,
    Entity,
    Transcript,
    MeetingAnalysis,
    ActionItem,
)


class IntentExtractor:
    """
    Extracts structured intents from meeting transcripts using LLM.

    Outputs: decisions, action_items, open_questions, commitments, summary.
    """

    SYSTEM_PROMPT = (
        "You are a meeting analysis expert. Analyze the transcribed meeting "
        "conversation and extract structured information.\n\n"
        "Extract these intent types:\n"
        "1. DECISION — a formal decision made during the meeting\n"
        "2. ACTION_ITEM — a task assigned to someone (with or without deadline)\n"
        "3. OPEN_QUESTION — a question raised that wasn't answered\n"
        "4. COMMITMENT — a promise someone made\n"
        "5. INFO — important information shared\n\n"
        "For each intent provide: type, content, confidence (0-1), speaker, "
        "timestamp (seconds), entities [{type, value}].\n\n"
        "Also provide:\n"
        "- summary: 2-3 sentence meeting summary\n"
        "- decisions: list of decision strings\n"
        "- action_items: list of {who, what, when}\n"
        "- open_questions: list of question strings\n"
        "- commitments: list of commitment strings\n\n"
        "Output valid JSON only."
    )

    USER_PROMPT_TEMPLATE = (
        "Meeting transcript:\n\n{transcript}\n\n"
        "Extract intents and analysis as JSON:\n"
        '{{\n'
        '  "intents": [\n'
        '    {{\n'
        '      "type": "decision|action_item|open_question|commitment|info",\n'
        '      "content": "...",\n'
        '      "confidence": 0.95,\n'
        '      "speaker": "Name",\n'
        '      "timestamp": 1.5,\n'
        '      "entities": [{{"type": "person", "value": "Name"}}]\n'
        '    }}\n'
        '  ],\n'
        '  "summary": "2-3 sentence summary",\n'
        '  "decisions": ["..."],\n'
        '  "action_items": [{{"who": "Name", "what": "task", "when": "date"}}],\n'
        '  "open_questions": ["..."],\n'
        '  "commitments": ["..."]\n'
        '}}'
    )

    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini",
    ):
        """
        Args:
            client: OpenAI-compatible async client. ``None`` activates mock mode.
            model:  Model name to use for chat completions.
        """
        self.client = client
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract(
        self,
        transcript: Transcript,
        meeting_id: str = "",
    ) -> MeetingAnalysis:
        """Extract intents from *transcript* and return a ``MeetingAnalysis``."""
        if not transcript.segments:
            raise ValueError("Cannot extract intents from an empty transcript")

        transcript_text = self._build_transcript_text(transcript)

        if self.client is not None:
            raw = await self._call_llm(transcript_text)
            return self._parse_response(raw, meeting_id or self._gen_id())
        else:
            return self._mock_response(transcript, meeting_id or "meeting-mock")

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    async def _call_llm(self, transcript_text: str) -> dict:
        """Call the LLM and return the parsed JSON dict."""
        user_prompt = self.USER_PROMPT_TEMPLATE.format(transcript=transcript_text)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, data: dict, meeting_id: str) -> MeetingAnalysis:
        """Parse raw LLM JSON into a validated ``MeetingAnalysis``."""
        intents: list[Intent] = []
        for i, raw_intent in enumerate(data.get("intents", [])):
            try:
                intent_type = IntentType(raw_intent.get("type", "info"))
            except ValueError:
                intent_type = IntentType.INFO

            intents.append(
                Intent(
                    id=f"intent-{i + 1}",
                    type=intent_type,
                    content=raw_intent.get("content", ""),
                    confidence=float(raw_intent.get("confidence", 0.5)),
                    speaker=raw_intent.get("speaker", "Unknown"),
                    timestamp=float(raw_intent.get("timestamp", 0)),
                    entities=[
                        Entity(type=e.get("type", ""), value=e.get("value", ""))
                        for e in raw_intent.get("entities", [])
                    ],
                )
            )

        action_items = [
            ActionItem(
                who=item.get("who"),
                what=item.get("what", ""),
                when=item.get("when"),
            )
            for item in data.get("action_items", [])
        ]

        return MeetingAnalysis(
            meeting_id=meeting_id,
            summary=data.get("summary", ""),
            intents=intents,
            decisions=data.get("decisions", []),
            action_items=action_items,
            open_questions=data.get("open_questions", []),
            commitments=data.get("commitments", []),
        )

    # ------------------------------------------------------------------
    # Mock path (testing without LLM)
    # ------------------------------------------------------------------

    def _mock_response(
        self, transcript: Transcript, meeting_id: str
    ) -> MeetingAnalysis:
        """Keyword-based mock for testing without an LLM."""
        intents: list[Intent] = []

        for i, seg in enumerate(transcript.segments):
            text_lower = seg.text.lower()

            if any(w in text_lower for w in ("decide", "decision", "agreed", "let's go with")):
                itype = IntentType.DECISION
            elif any(w in text_lower for w in ("will do", "i'll", "commit", "promise")):
                itype = IntentType.COMMITMENT
            elif "?" in text_lower or any(w in text_lower for w in ("what about", "how do we")):
                itype = IntentType.OPEN_QUESTION
            elif any(w in text_lower for w in ("prepare", "finish", "send", "create", "do the")):
                itype = IntentType.ACTION_ITEM
            else:
                itype = IntentType.INFO

            intents.append(
                Intent(
                    id=f"intent-{i + 1}",
                    type=itype,
                    content=seg.text,
                    confidence=0.8,
                    speaker=seg.speaker,
                    timestamp=seg.start_time,
                    entities=[],
                )
            )

        decisions = [i.content for i in intents if i.type == IntentType.DECISION]
        action_items = [
            ActionItem(what=i.content, who=i.speaker)
            for i in intents
            if i.type == IntentType.ACTION_ITEM
        ]
        commitments = [i.content for i in intents if i.type == IntentType.COMMITMENT]
        open_questions = [i.content for i in intents if i.type == IntentType.OPEN_QUESTION]

        speakers = list({s.speaker for s in transcript.segments})
        summary = f"Meeting with {', '.join(speakers)} covering {len(intents)} topics."

        return MeetingAnalysis(
            meeting_id=meeting_id,
            summary=summary,
            intents=intents,
            decisions=decisions,
            action_items=action_items,
            open_questions=open_questions,
            commitments=commitments,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_transcript_text(transcript: Transcript) -> str:
        return "\n".join(
            f"[{seg.start_time:.1f}s] {seg.speaker}: {seg.text}"
            for seg in transcript.segments
        )

    @staticmethod
    def _gen_id() -> str:
        return f"meeting-{uuid.uuid4().hex[:8]}"
