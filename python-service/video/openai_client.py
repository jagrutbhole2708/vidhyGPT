"""
OpenAI Client — GPT-4o-mini for ALL video pipeline tasks.

Handles:
  1. Video script generation (scene planning + voiceover narration)
  2. Visual content extraction from narration
  3. Manim code generation support

Provides both async (generate_with_gpt4) and sync-compatible (generate_json)
interfaces for different parts of the pipeline.
"""

import os
import json
import logging
from openai import AsyncOpenAI, OpenAI

from dotenv import load_dotenv

load_dotenv()
LOGGER = logging.getLogger(__name__)

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Async client (for manim_code_generator extraction helpers)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Sync client (for script_generator, which wraps in asyncio.to_thread)
sync_client = OpenAI(api_key=OPENAI_API_KEY)


# ── Exception classes (drop-in replacements for GeminiClientError) ──

class OpenAIClientError(RuntimeError):
    """Base error type for OpenAI client failures."""


class OpenAIQuotaError(OpenAIClientError):
    """Raised when OpenAI rate limits are hit."""


class OpenAINetworkError(OpenAIClientError):
    """Raised on transient network/service issues."""


# ── Async interface (used by manim_code_generator) ──

async def generate_with_gpt4(system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
    """
    Call GPT-4o async for content extraction / code generation.
    Returns the raw response text.
    """
    if not OPENAI_API_KEY:
        raise OpenAIClientError("Missing OPENAI_API_KEY in .env")

    kwargs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await async_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        LOGGER.info("GPT-4o-mini async response: %d chars", len(content) if content else 0)
        return content
    except Exception as exc:
        error_str = str(exc).lower()
        if "429" in error_str or "rate" in error_str or "quota" in error_str:
            raise OpenAIQuotaError(f"OpenAI rate limit: {exc}") from exc
        if "connection" in error_str or "network" in error_str:
            raise OpenAINetworkError(f"Network issue: {exc}") from exc
        LOGGER.error("GPT-4o-mini API error: %s", exc)
        raise OpenAIClientError(f"OpenAI error: {exc}") from exc


# ── Sync interface (used by script_generator via asyncio.to_thread) ──

def generate_json(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 4000,
) -> str:
    """
    Synchronous GPT-4o-mini call that returns a JSON string.
    Drop-in replacement for gemini_client.generate_json().

    The prompt is treated as the user message.
    JSON mode is always enabled.
    """
    if not OPENAI_API_KEY:
        raise OpenAIClientError("Missing OPENAI_API_KEY in .env")

    try:
        response = sync_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educational video script writer. Always respond with valid JSON only."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise OpenAIClientError("GPT-4o-mini returned empty response")
        LOGGER.info("GPT-4o-mini sync response: %d chars", len(content))
        return content

    except OpenAIClientError:
        raise
    except Exception as exc:
        error_str = str(exc).lower()
        if "429" in error_str or "rate" in error_str or "quota" in error_str:
            raise OpenAIQuotaError(f"OpenAI rate limit: {exc}") from exc
        if "connection" in error_str or "network" in error_str:
            raise OpenAINetworkError(f"Network issue: {exc}") from exc
        LOGGER.error("GPT-4o-mini sync error: %s", exc)
        raise OpenAIClientError(f"OpenAI error: {exc}") from exc
