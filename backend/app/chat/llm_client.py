from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import google.generativeai as genai
from groq import AsyncGroq

from app.config import settings

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-2.5-flash"
_GROQ_MODEL = "llama-3.1-8b-instant"

# How long to wait after a 429 before retrying (seconds)
_GEMINI_RETRY_DELAY = 4.0
_GROQ_RETRY_DELAY = 2.0
_GROQ_MAX_RETRIES = 3


def _gemini_client() -> genai.GenerativeModel:
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(_GEMINI_MODEL)


def _groq_client() -> AsyncGroq:
    return AsyncGroq(api_key=settings.groq_api_key)


async def _stream_gemini(
    messages: list[dict],
) -> AsyncIterator[tuple[str, str]]:
    """Yields (token, model_name) pairs from Gemini."""
    client = _gemini_client()
    # Convert OpenAI-style messages to Gemini format
    history = []
    for m in messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        history.append({"role": role, "parts": [m["content"]]})

    last = messages[-1]["content"]
    chat = client.start_chat(history=history)

    response = await chat.send_message_async(last, stream=True)
    async for chunk in response:
        # chunk.text raises if the response was blocked; guard it
        try:
            text = chunk.text
        except Exception:
            continue
        if text:
            yield text, _GEMINI_MODEL


async def _stream_groq(
    messages: list[dict],
) -> AsyncIterator[tuple[str, str]]:
    """Yields (token, model_name) pairs from Groq."""
    client = _groq_client()
    stream = await client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=messages,  # type: ignore[arg-type]
        stream=True,
        max_tokens=2048,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta, _GROQ_MODEL


async def stream_response(
    messages: list[dict],
) -> AsyncIterator[tuple[str, str]]:
    """
    Primary: Gemini 1.5 Flash.
    On 429 or any error → retry once after delay → fallback to Groq.
    Yields (token, model_name).
    Raises RuntimeError if both providers fail.
    """
    # --- Try Gemini ---
    if settings.gemini_api_key:
        for attempt in range(2):
            try:
                async for token, model in _stream_gemini(messages):
                    yield token, model
                return
            except Exception as exc:
                msg = str(exc).lower()
                is_rate_limit = "429" in msg or "quota" in msg or "rate" in msg
                if is_rate_limit and attempt == 0:
                    logger.warning("Gemini 429 — waiting %.1fs then retrying", _GEMINI_RETRY_DELAY)
                    await asyncio.sleep(_GEMINI_RETRY_DELAY)
                    continue
                logger.warning("Gemini failed (%s) — falling back to Groq", type(exc).__name__)
                break
    else:
        logger.info("GEMINI_API_KEY not set — going straight to Groq")

    # --- Fallback: Groq ---
    if not settings.groq_api_key:
        raise RuntimeError("Both Gemini and Groq are unavailable (no API keys configured).")

    delay = _GROQ_RETRY_DELAY
    for attempt in range(_GROQ_MAX_RETRIES):
        try:
            async for token, model in _stream_groq(messages):
                yield token, model
            return
        except Exception as exc:
            msg = str(exc).lower()
            is_rate_limit = "429" in msg or "rate" in msg
            if is_rate_limit and attempt < _GROQ_MAX_RETRIES - 1:
                logger.warning("Groq 429 — waiting %.1fs (attempt %d)", delay, attempt + 1)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            raise RuntimeError(f"Groq failed after {attempt + 1} attempt(s): {exc}") from exc
