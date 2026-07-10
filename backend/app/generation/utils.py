from __future__ import annotations


def strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences that LLMs sometimes add."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()
