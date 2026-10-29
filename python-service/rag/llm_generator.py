"""
LLM Generator — generates structured answers using Groq (primary) or Gemini (fallback).

Switch between providers via LLM_PROVIDER env var:
  LLM_PROVIDER=groq    (default, uses Groq API with Qwen3 model)
  LLM_PROVIDER=gemini  (uses Gemini REST API)
"""

import os
import json
import logging
import requests
from dotenv import load_dotenv
from constants.SystemPrompt import ANSWER_SYSTEM_PROMPT

load_dotenv()

LOGGER = logging.getLogger(__name__)

# ── Provider config ──
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

# Groq config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Gemini config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

SYSTEM_PROMPT = ANSWER_SYSTEM_PROMPT


def build_user_prompt(
    question: str, chunks: list, board: str, class_level: str, subject: str
) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}] Class {chunk['class']} {chunk['subject']} | Chapter: {chunk.get('chapter','N/A')}\n"
            f"Q: {chunk.get('question', '')}\n"
            f"A: {chunk['text']}"
        )

    context = "\n\n".join(context_parts)

    if context.strip():
        # We have NCERT content — use it as reference
        return f"""Student Context: {board} | Class {class_level} | {subject}
Student Question: {question}

NCERT Textbook Content (for reference):
{context}

Use the NCERT content as a reference if it is relevant. If the NCERT content does not cover this topic well, use your own knowledge to give a thorough, accurate answer. The student deserves a complete explanation regardless.

Generate your response as JSON."""
    else:
        # No NCERT content found — answer purely from AI knowledge
        return f"""Student Context: {board} | Class {class_level} | {subject}
Student Question: {question}

No NCERT textbook content was found for this topic. Answer this question entirely from your own knowledge. Make sure your answer is accurate, detailed, and appropriate for a Class {class_level} {board} student. Follow the {board} syllabus level and explain in simple, clear language.

Generate your response as JSON."""


# ═══════════════════════════════════════════════════════════════════
# GROQ PROVIDER (OpenAI-compatible API)
# ═══════════════════════════════════════════════════════════════════

def _call_groq(system_prompt: str, user_prompt: str) -> dict:
    """Call Groq API (OpenAI-compatible). Returns parsed JSON dict."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Check if using a Qwen3 model (needs reasoning controls for JSON mode)
    is_qwen3 = "qwen3" in GROQ_MODEL.lower()

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6 if is_qwen3 else 0.3,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    # Qwen3 with JSON mode requires reasoning_format to be "hidden" or "parsed"
    if is_qwen3:
        payload["reasoning_format"] = "hidden"

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=120.0)
    except requests.RequestException as exc:
        LOGGER.error("Groq network error: %s", exc)
        raise ValueError(f"Groq network error: {exc}") from exc

    data = resp.json()

    if resp.status_code != 200:
        error_msg = data.get("error", {}).get("message", str(data))
        LOGGER.error("Groq API error (%s): %s", resp.status_code, error_msg)
        raise ValueError(f"Groq API Error ({resp.status_code}): {error_msg}")

    try:
        raw = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        LOGGER.error("Unexpected Groq response: %s", data)
        raise ValueError(f"Failed to parse Groq response: {exc}") from exc

    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════════
# GEMINI PROVIDER (REST API)
# ═══════════════════════════════════════════════════════════════════

def _call_gemini(system_prompt: str, user_prompt: str) -> dict:
    """Call Gemini REST API. Returns parsed JSON dict."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    full_prompt = system_prompt + "\n\n" + user_prompt
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4000,
            "responseMimeType": "application/json",
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=60.0)
    except requests.RequestException as exc:
        LOGGER.error("Gemini network error: %s", exc)
        raise ValueError(f"Gemini network error: {exc}") from exc

    data = resp.json()

    if resp.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Unknown error")
        LOGGER.error("Gemini API error (%s): %s", resp.status_code, error_msg)
        raise ValueError(f"Gemini API Error ({resp.status_code}): {error_msg}")

    try:
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in Gemini response")
        raw = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        LOGGER.error("Unexpected Gemini response structure: %s", data)
        raise ValueError(f"Failed to parse Gemini response: {exc}") from exc

    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════════
# POST-PROCESSING — fix LaTeX rendering in answers
# ═══════════════════════════════════════════════════════════════════

def _fix_latex_in_answer(result: dict) -> dict:
    """
    Fix LaTeX backslashes that get eaten by JSON parsing.
    
    When the LLM generates \\text{Ar-NH} in JSON, json.loads() interprets:
      \\t → tab character  (\\text → <tab>ext)
      \\r → carriage return (\\rightarrow → <CR>ightarrow)
      \\n → newline        (\\nu → <newline>u)
      \\f → form feed      (\\frac → <FF>rac)
      \\b → backspace      (\\beta → <BS>eta)
    
    This function detects and restores these broken LaTeX commands.
    """
    answer = result.get("answer", "")
    if not answer:
        return result
    
    # Fix JSON-escaped control characters back to LaTeX commands
    # Order matters — fix the most specific patterns first
    latex_fixes = [
        ('\text', '\\text'),       # tab + "ext" → \text
        ('\rightarrow', '\\rightarrow'),  # CR + "ightarrow" → \rightarrow
        ('\r', '\\r'),             # bare CR
        ('\t', '\\t'),             # bare tab (if not already fixed)
        ('\n', '\n'),              # keep actual newlines as-is (they're markdown line breaks)
        ('\frac', '\\frac'),       # form feed + "rac" → \frac
        ('\f', '\\f'),             # bare FF
        ('\b', '\\b'),             # bare backspace
    ]
    
    # More targeted approach: look for known LaTeX command fragments
    import re as _re
    
    # Fix: <tab>ext{ → \text{
    answer = answer.replace('\text{', '\\text{')
    answer = answer.replace('\textbf{', '\\textbf{')
    answer = answer.replace('\textrm{', '\\textrm{')
    answer = answer.replace('\textit{', '\\textit{')
    
    # Fix: <CR>ightarrow → \rightarrow
    answer = answer.replace('\rightarrow', '\\rightarrow')
    answer = answer.replace('\rightleftharpoons', '\\rightleftharpoons')
    
    # Fix: <FF>rac → \frac
    answer = answer.replace('\frac', '\\frac')
    
    # Fix: <BS>eta → \beta, etc.
    answer = answer.replace('\beta', '\\beta')
    answer = answer.replace('\begin', '\\begin')
    
    # Fix bare control chars that aren't part of LaTeX commands
    # Replace stray tabs/CRs that aren't newlines
    answer = answer.replace('\r\n', '\n')  # normalize CRLF first
    answer = answer.replace('\r', '')       # remove stray CRs
    answer = answer.replace('\t', ' ')      # replace stray tabs with space
    answer = answer.replace('\f', '')       # remove stray form feeds
    answer = answer.replace('\b', '')       # remove stray backspaces
    
    # Also fix common pattern: bare "ightarrow" without backslash (from eaten \r)
    answer = _re.sub(r'(?<![\\a-zA-Z])ightarrow', r'\\rightarrow', answer)
    # Fix "ext{" without preceding backslash (from eaten \t)
    answer = _re.sub(r'(?<![\\a-zA-Z])ext\{', r'\\text{', answer)
    # Fix "rac{" without preceding backslash (from eaten \f)
    answer = _re.sub(r'(?<![\\a-zA-Z])rac\{', r'\\frac{', answer)
    
    result["answer"] = answer
    return result


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

async def generate_answer_and_script(
    question: str,
    chunks: list,
    board: str = "CBSE",
    class_level: str = "7",
    subject: str = "Science",
) -> dict:
    """Generate answer using configured LLM provider (groq or gemini)."""
    user_prompt = build_user_prompt(question, chunks, board, class_level, subject)

    provider = LLM_PROVIDER
    LOGGER.info("Using LLM provider: %s (model: %s)", provider, GROQ_MODEL if provider == "groq" else GEMINI_MODEL)

    try:
        if provider == "gemini":
            result = _call_gemini(SYSTEM_PROMPT, user_prompt)
        else:
            # Default: Groq
            result = _call_groq(SYSTEM_PROMPT, user_prompt)
    except (ValueError, json.JSONDecodeError) as e:
        # If primary fails, try the other provider as fallback
        fallback = "gemini" if provider != "gemini" else "groq"
        LOGGER.warning("%s failed (%s), trying %s as fallback...", provider, e, fallback)
        try:
            if fallback == "gemini":
                result = _call_gemini(SYSTEM_PROMPT, user_prompt)
            else:
                result = _call_groq(SYSTEM_PROMPT, user_prompt)
        except Exception as fallback_err:
            LOGGER.error("Both providers failed. Primary: %s, Fallback: %s", e, fallback_err)
            raise ValueError(f"All LLM providers failed. {provider}: {e} | {fallback}: {fallback_err}")

    # Post-process: fix LaTeX backslashes eaten by JSON parsing
    result = _fix_latex_in_answer(result)

    return result

