# Processing Module — DEFERRED

This module is **deferred to Phase 2** (audio pipeline).

## Why

The `understanding/batch/transcription.py` already handles text-to-Transcript conversion for the MVP text pipeline. The `processing/` module was designed for the full audio path (Whisper + diarization + chunking), which overlaps with `understanding/batch/`.

## Phase 2 Plan

When we add real audio support:
1. Move Whisper integration here (`processing/transcription/whisper.py`)
2. Add pyannote diarization (`processing/diarization/pyannote.py`)
3. `understanding/batch/transcription.py` becomes a thin wrapper that delegates to `processing/`

## Current Structure (stubs only)

```
processing/
├── DEFERRED.md          # This file
├── CONTEXT.md           # Original architecture doc
├── __init__.py          # Empty
├── transcription/
│   └── __init__.py      # Empty
└── diarization/
    └── __init__.py      # Empty
```

Do not add implementation code here until Phase 2.
