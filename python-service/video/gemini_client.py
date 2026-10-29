"""
Gemini client using the google-genai package.
Uses: from google import genai (NOT google.generativeai)
"""

import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "gemini-2.0-flash"
DEFAULT_MAX_OUTPUT_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.3


class GeminiClientError(RuntimeError):
    """Base error type for Gemini client failures."""


class GeminiQuotaError(GeminiClientError):
    """Raised when Gemini quota or rate limits are exceeded."""


class GeminiNetworkError(GeminiClientError):
    """Raised when a transient network/service issue occurs."""


def _get_client() -> genai.Client:
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise GeminiClientError("Missing GEMINI_API_KEY in environment")
    return genai.Client(api_key=api_key)


def generate_text(
    prompt: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
) -> str:
    """
    Generate text using the google-genai SDK.
    Returns the raw text response.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    model_name = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL_NAME).strip()
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    max_tokens = max_output_tokens if max_output_tokens is not None else DEFAULT_MAX_OUTPUT_TOKENS

    config_kwargs = {
        "temperature": temp,
        "max_output_tokens": max_tokens,
    }
    if response_mime_type:
        config_kwargs["response_mime_type"] = response_mime_type

    config = types.GenerateContentConfig(**config_kwargs)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        text = response.text
        if not text:
            raise GeminiClientError("Gemini returned empty response")
        return text

    except GeminiClientError:
        raise
    except Exception as exc:
        error_str = str(exc).lower()
        if "429" in error_str or "quota" in error_str or "rate" in error_str:
            raise GeminiQuotaError(f"Gemini quota exceeded: {exc}") from exc
        if "network" in error_str or "connection" in error_str:
            raise GeminiNetworkError(f"Network issue: {exc}") from exc
        LOGGER.error("Gemini generation failed: %s", exc)
        raise GeminiClientError(f"Gemini error: {exc}") from exc


def generate_json(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 2000,
) -> str:
    """
    Generate text with response_mime_type set to application/json.
    Returns raw JSON string (caller must parse).
    """
    return generate_text(
        prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
    )