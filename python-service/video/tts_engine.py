"""
TTS Engine — generates MP3 audio per scene.

Primary: Fish Audio API (natural, teacher-quality voice) using sync requests.
Fallback: gTTS (reliable, no GPU, works everywhere).
Returns exact duration (float, seconds) measured by ffprobe.
"""

import logging
import os
import re
import subprocess
from pathlib import Path

import requests as http_requests
from dotenv import load_dotenv

load_dotenv()
LOGGER = logging.getLogger(__name__)

# ── Fish Audio config ──
FISH_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_API_URL = "https://api.fish.audio/v1/tts"
# Fish Audio reference voice ID for a clear, warm teacher voice
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID", "")


# ────────────────────────────────────────────────────────────
# Narration pre-processing
# ────────────────────────────────────────────────────────────


def preprocess_narration(text: str) -> str:
    """
    Clean narration for natural speech.
    Remove LaTeX, clean special characters, replace math symbols with words.
    """
    # Step 0: Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold** → bold
    text = re.sub(r'__(.+?)__', r'\1', text)        # __italic__ → italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)         # *italic* → italic
    text = re.sub(r'_(.+?)_', r'\1', text)           # _italic_ → italic
    text = re.sub(r'#{1,6}\s*', '', text)             # ## headings → remove
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullet points
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r'>\s*', '', text)                  # blockquotes

    # Step 1: Extract text from \text{...}, \textbf{...}, \mathrm{...} etc.
    # e.g., \text{Ar-NH}_2 → Ar-NH_2
    text = re.sub(r'\\text(?:bf|rm|it|sf)?\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', text)

    # Step 2: Remove LaTeX math delimiters and their content
    text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    text = re.sub(r'\$.*?\$', '', text)

    # Step 3: Remove remaining LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'[{}]', '', text)

    # Step 4: Clean subscripts/superscripts notation
    text = re.sub(r'_\{?(\w+)\}?', r' \1', text)  # _2 or _{2} → 2
    text = re.sub(r'\^\{?(\w+)\}?', r' \1', text)  # ^2 or ^{2} → 2

    # Step 5: Replace common math symbols with words
    replacements = {
        '²': ' squared',
        '³': ' cubed',
        '≈': ' approximately ',
        '∝': ' is proportional to ',
        '∑': ' sum of ',
        '∫': ' integral of ',
        '→': ' gives ',
        '⇌': ' is in equilibrium with ',
        '≡': ' is equivalent to ',
        'α': 'alpha',
        'β': 'beta',
        'γ': 'gamma',
        'λ': 'lambda',
        'ω': 'omega',
        'π': 'pi',
        'μ': 'mu',
        'θ': 'theta',
        '°': ' degrees',
    }
    for symbol, word in replacements.items():
        text = text.replace(symbol, word)

    # Step 6: Clean up artifacts
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ────────────────────────────────────────────────────────────
# Fish Audio TTS (Primary) — SYNC using requests
# ────────────────────────────────────────────────────────────


def _generate_fish_audio(narration: str, output_path: str) -> float:
    """
    Generate audio using Fish Audio API (sync, using requests).
    Follows the official Fish Audio docs exactly.
    Returns exact duration in seconds.
    """
    payload = {
        "text": narration,
        "format": "mp3",
        "mp3_bitrate": 128,
        "normalize": True,
        "latency": "normal",
        "chunk_length": 300,
        "temperature": 0.7,
        "top_p": 0.7,
        "repetition_penalty": 1.2,
        "prosody": {
            "speed": 1,
            "volume": 0,
            "normalize_loudness": True,
        },
    }

    # Add reference voice if configured
    if FISH_VOICE_ID:
        payload["reference_id"] = FISH_VOICE_ID

    headers = {
        "model": "s2-pro",
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
    }

    response = http_requests.post(
        FISH_API_URL,
        json=payload,
        headers=headers,
        timeout=90,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Fish Audio API error {response.status_code}: {response.text[:200]}"
        )

    # Save the audio bytes to file
    with open(output_path, "wb") as f:
        f.write(response.content)

    LOGGER.info(
        "Fish Audio: saved %d bytes → %s",
        len(response.content),
        Path(output_path).name,
    )

    # Add 0.5s silence padding at end for smoother transitions
    _add_silence_padding(output_path, pad_seconds=0.5)

    return get_audio_duration(output_path)


# ────────────────────────────────────────────────────────────
# Core generate_audio (fully sync — no event loop issues)
# ────────────────────────────────────────────────────────────


def generate_audio(narration: str, output_path: str) -> float:
    """
    Generate audio from narration text.
    Primary: Fish Audio API (if API key configured).
    Fallback: gTTS (always available).
    Returns exact duration in seconds as a float (measured by ffprobe).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Pre-process narration for better speech
    processed_text = preprocess_narration(narration)

    # ── Try Fish Audio first (if API key is set) ──
    if FISH_API_KEY:
        try:
            duration = _generate_fish_audio(processed_text, output_path)
            LOGGER.info(
                "Fish Audio generated: %s (%.1fs)",
                Path(output_path).name,
                duration,
            )
            return duration
        except Exception as exc:
            LOGGER.warning("Fish Audio failed (%s), falling back to gTTS", exc)

    # ── Fallback to gTTS ──
    _generate_gtts(processed_text, output_path)

    # ── Add silence padding ──
    _add_silence_padding(output_path, pad_seconds=0.5)

    duration = get_audio_duration(output_path)
    LOGGER.info(
        "Audio generated (gTTS fallback): %s (%.1fs)",
        Path(output_path).name,
        duration,
    )
    return duration


# ────────────────────────────────────────────────────────────
# gTTS Fallback
# ────────────────────────────────────────────────────────────


def _generate_gtts(text: str, output_path: str) -> None:
    """Fallback: generate audio using gTTS."""
    from gtts import gTTS

    LOGGER.info("Using gTTS for: %s...", text[:50])
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)


# ────────────────────────────────────────────────────────────
# Silence padding
# ────────────────────────────────────────────────────────────


def _add_silence_padding(audio_path: str, pad_seconds: float = 0.5) -> None:
    """Append silence to the end of the audio file."""
    if not Path(audio_path).exists():
        return

    tmp_path = audio_path + ".padded.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                audio_path,
                "-af",
                f"apad=pad_dur={pad_seconds}",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if Path(tmp_path).exists() and Path(tmp_path).stat().st_size > 0:
            os.replace(tmp_path, audio_path)
    except subprocess.TimeoutExpired:
        LOGGER.warning("FFmpeg silence padding timed out; keeping original")
    except FileNotFoundError:
        LOGGER.warning("FFmpeg not found — skipping silence padding")
    finally:
        if Path(tmp_path).exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ────────────────────────────────────────────────────────────
# Duration helper
# ────────────────────────────────────────────────────────────


def get_audio_duration(audio_path: str) -> float:
    """Get exact duration of audio file using ffprobe. Falls back to pydub, then 10.0s."""
    if not Path(audio_path).exists():
        LOGGER.error("Audio file not found: %s", audio_path)
        return 10.0

    # Try ffprobe first
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        duration = float(result.stdout.strip())
        return duration
    except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback to pydub
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as exc:
        LOGGER.warning(
            "Duration measurement failed for %s: %s. Using 10.0s fallback.",
            audio_path,
            exc,
        )
        return 10.0
