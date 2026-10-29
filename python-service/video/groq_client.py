"""
Groq LLM client — drop-in replacement for gemini_client.
Uses Groq's OpenAI-compatible API with llama-3.3-70b-versatile.
"""

import logging
import os
from threading import Lock
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)
_LOCK = Lock()

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 4096
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClientError(RuntimeError):
    """Base error for Groq client failures."""


class GroqQuotaError(GroqClientError):
    """Rate-limit or quota exceeded."""


class GroqNetworkError(GroqClientError):
    """Transient network issue."""


def _get_api_key() -> str:
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not key:
        raise GroqClientError("Missing GROQ_API_KEY in environment")
    return key


def _get_model() -> str:
    return (os.getenv("GROQ_MODEL") or DEFAULT_MODEL).strip()


def generate_text(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """
    Send a prompt to Groq and return the text response.

    Supports optional system prompt, temperature, and max_tokens overrides.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    api_key = _get_api_key()
    model = _get_model()
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    max_tok = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tok,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(GROQ_API_URL, json=payload, headers=headers)

        if resp.status_code == 429:
            LOGGER.error("Groq rate-limit hit (429)")
            raise GroqQuotaError("Groq rate-limit exceeded (429)")

        if resp.status_code >= 500:
            LOGGER.error("Groq server error (%s): %s", resp.status_code, resp.text[:300])
            raise GroqNetworkError(f"Groq server error ({resp.status_code})")

        if resp.status_code != 200:
            LOGGER.error("Groq API error (%s): %s", resp.status_code, resp.text[:300])
            raise GroqClientError(f"Groq API error ({resp.status_code})")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise GroqClientError("Groq response contained no choices")

        text = choices[0].get("message", {}).get("content", "").strip()
        if not text:
            raise GroqClientError("Groq response contained empty content")

        return text

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        LOGGER.error("Groq network error: %s", exc)
        raise GroqNetworkError("Network error calling Groq API") from exc
    except GroqClientError:
        raise
    except Exception as exc:
        LOGGER.exception("Unexpected Groq client error")
        raise GroqClientError("Unexpected Groq client error") from exc
