# Contributing to mainframe

## Agent-Friendly Code Standards

This project is designed with the understanding that **the maintainers of tomorrow may be AI agents**. Every decision is made with that future in mind.

### 1. Each Module Must Have a CONTEXT.md

Every module directory must contain a `CONTEXT.md` explaining:
- **What this does**: One sentence
- **Why it exists**: Design rationale
- **Key concepts**: Core concepts and data structures
- **Interfaces**: Input/Output contracts

### 2. Pydantic Models for All Data Contracts

Never pass raw dicts between modules. Every data contract must be a Pydantic model:

```python
from pydantic import BaseModel

class Intent(BaseModel):
    type: IntentType
    content: str
    confidence: float
```

### 3. Single File Limit: 300 Lines

If a file exceeds 300 lines, split it. Agents can reason about smaller files better.

### 4. Every Public Function Needs Documentation

```python
async def extract_intent(transcript: Transcript) -> Intent:
    """
    Extract intent from a single transcript segment.
    
    Args:
        transcript: A single speaker's turn in the meeting
        
    Returns:
        Intent with type, content, and confidence score
    """
```

### 5. Test Coverage > 80% for Core Modules

- `understanding/` modules: 80%+ coverage required
- `router/` modules: 80%+ coverage required
- `processing/` modules: 60%+ coverage acceptable

## Development Workflow

```bash
# Clone
git clone git@github.com:firenzemc/mainframe.git
cd mainframe

# Setup
pip install -e ".[dev]"

# Test
pytest

# Type check
ruff check src/
mypy src/
```

## Code Review Principles

- Does this module have a CONTEXT.md?
- Are all data contracts Pydantic models?
- Is any single file > 300 lines?
- Does every public function have a docstring?
- Are there tests for core logic?

---

*This is an agent-era project. Write code that agents can understand.*
