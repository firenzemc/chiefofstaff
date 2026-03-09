# Processing Module

## What this does
Processes raw audio into transcribed text with speaker labels.

## Why it exists
Raw audio isn't actionable. We need transcription + speaker diarization to understand who said what.

## Key concepts

- **Transcription**: Whisper (faster-whisper for GPU acceleration)
- **Diarization**: pyannote.audio for speaker separation
- **Chunking**: Split long audio into manageable segments

## Interfaces

```python
class TranscriptSegment(BaseModel):
    speaker: str
    text: str
    start_time: float
    end_time: float

class Transcript(BaseModel):
    segments: List[TranscriptSegment]
    language: str
    duration: float
```
