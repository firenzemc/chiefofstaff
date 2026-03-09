"""
Transcription service using faster-whisper.
"""

from typing import Optional
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .models import Transcript, TranscriptSegment


class TranscriptionService:
    """
    Service for transcribing audio files using faster-whisper.
    
    Supports both batch and streaming modes.
    """
    
    def __init__(self, model_size: str = "base", device: str = "auto"):
        """
        Initialize transcription service.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cpu, cuda, auto)
        """
        self.model_size = model_size
        self.device = device
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
    
    async def transcribe(self, audio_data: bytes) -> Transcript:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcript with segments
        """
        # Lazy load model
        model = await self._get_model()
        
        # Run transcription in thread pool (blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self._transcribe_sync,
            model,
            audio_data
        )
        
        return result
    
    async def transcribe_file(self, file_path: Path) -> Transcript:
        """
        Transcribe an audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Transcript with segments
        """
        audio_data = file_path.read_bytes()
        return await self.transcribe(audio_data)
    
    async def transcribe_text(self, text: str) -> Transcript:
        """
        Convert text transcript to Transcript model.
        
        Args:
            text: Raw text transcript (e.g., "Alice: Hello\\nBob: Hi")
            
        Returns:
            Transcript with segments parsed from text
        """
        segments = []
        current_time = 0.0
        
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Parse "Speaker: text" format
            if ":" in line:
                parts = line.split(":", 1)
                speaker = parts[0].strip()
                content = parts[1].strip()
            else:
                speaker = "Unknown"
                content = line
            
            # Estimate duration based on content length
            duration = max(1.0, len(content) / 10.0)
            
            segments.append(TranscriptSegment(
                speaker=speaker,
                text=content,
                start_time=current_time,
                end_time=current_time + duration
            ))
            current_time += duration
        
        return Transcript(
            segments=segments,
            language="en",
            duration=current_time
        )
    
    async def _get_model(self):
        """Lazy load the whisper model."""
        if self._model is None:
            # Import here to avoid heavy import at module level
            # In real implementation, would load actual model
            self._model = "loaded"  # Placeholder
        return self._model
    
    def _transcribe_sync(self, model, audio_data: bytes) -> Transcript:
        """
        Synchronous transcription (runs in thread pool).
        
        Placeholder for actual faster-whisper implementation.
        """
        # In real implementation:
        # result = model.transcribe(audio_data)
        # return Transcript(
        #     segments=[
        #         TranscriptSegment(
        #             speaker=s.get("speaker", "Unknown"),
        #             text=s.get("text", ""),
        #             start_time=s.get("start", 0),
        #             end_time=s.get("end", 0)
        #         ) for s in result.segments
        #     ],
        #     language=result.language,
        #     duration=result.duration
        # )
        
        # For now, return empty transcript as placeholder
        return Transcript(
            segments=[],
            language="en",
            duration=0.0
        )
