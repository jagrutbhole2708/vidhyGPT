"""
Manim Renderer — renders each scene to MP4 using manim CLI.
Uses -qm flag (720p 30fps). Includes FFmpeg fallback for failed renders.

On Windows, uses `python -m manim` to avoid PATH issues.
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# Render quality: -ql (480p 15fps, low RAM) or -qm (720p 30fps, high RAM)
# Use -ql for free-tier hosting (512MB RAM) to avoid OOM crashes
MANIM_QUALITY = os.getenv("MANIM_QUALITY", "-ql")


def _get_manim_command() -> list[str]:
    """
    Get the correct manim command for the current platform.
    On Windows, 'manim' may not be on PATH even if installed.
    Using 'python -m manim' is more reliable.
    """
    # Try the manim command directly first
    try:
        result = subprocess.run(
            ["manim", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return ["manim"]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: python -m manim (works when manim is installed in venv)
    return [sys.executable, "-m", "manim"]


def render_scene(
    manim_code: str,
    scene_class_name: str,
    output_path: str,
    duration_seconds: float,
    scene_index: int,
) -> bool:
    """
    Render a single Manim scene to MP4.
    Returns True on success.
    Falls back to FFmpeg text-on-black if Manim render fails.
    """
    # Write code to temp file
    temp_dir = Path(tempfile.mkdtemp(prefix=f"manim_s{scene_index}_"))
    script_file = temp_dir / f"scene_{scene_index}.py"
    script_file.write_text(manim_code, encoding="utf-8")

    media_dir = temp_dir / "media"

    manim_cmd = _get_manim_command()
    quality = MANIM_QUALITY
    LOGGER.info("Rendering scene %d with %s %s ...", scene_index, " ".join(manim_cmd), quality)

    try:
        result = subprocess.run(
            [
                *manim_cmd, "render",
                quality,                             # -ql = 480p 15fps (low RAM), -qm = 720p 30fps
                "--media_dir", str(media_dir),
                "--disable_caching",
                str(script_file),
                scene_class_name,
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max per scene (low quality is slower on weak CPUs)
        )
    except subprocess.TimeoutExpired:
        LOGGER.error("Scene %d render timed out after 180s", scene_index)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    except FileNotFoundError as exc:
        LOGGER.error(
            "Manim executable not found for scene %d: %s. "
            "Ensure manim is installed: pip install manim",
            scene_index, exc,
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    if result.returncode != 0:
        LOGGER.error(
            "Manim render failed for scene %d (exit %d):\nSTDERR: %s",
            scene_index, result.returncode, result.stderr[-800:] if result.stderr else "(empty)",
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # Find the rendered MP4
    rendered_files = list(media_dir.rglob("*.mp4"))
    if not rendered_files:
        LOGGER.error("No MP4 found after rendering scene %d", scene_index)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Move to final path (shutil.move handles cross-device)
    shutil.move(str(rendered_files[0]), output_path)
    LOGGER.info("Scene %d rendered → %s", scene_index, output_path)

    # Clean up
    shutil.rmtree(temp_dir, ignore_errors=True)
    return True


def render_fallback_ffmpeg(text: str, output_path: str, duration: float) -> bool:
    """
    Pure FFmpeg fallback: white text on black screen.
    Used when Manim render fails. Produces valid MP4 at correct duration.
    NEVER shows 'Generating animation...' — shows actual narration text.
    """
    # Sanitize text for FFmpeg drawtext
    safe = text.replace("'", " ").replace(":", " ").replace('"', " ").replace("\\", " ")
    # Wrap long text
    if len(safe) > 60:
        words = safe.split()
        lines = []
        current = []
        for w in words:
            current.append(w)
            if len(" ".join(current)) > 50:
                lines.append(" ".join(current))
                current = []
        if current:
            lines.append(" ".join(current))
        safe = "\\n".join(lines[:4])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:size=1280x720:duration={duration:.1f}:rate=30",
                "-vf", (
                    f"drawtext=text='{safe}':"
                    "fontsize=32:fontcolor=white:"
                    "x=(w-text_w)/2:y=(h-text_h)/2:"
                    "line_spacing=10"
                ),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            LOGGER.error("FFmpeg fallback failed: %s", result.stderr[-300:] if result.stderr else "")
            return False

        if Path(output_path).exists():
            LOGGER.info("Fallback video created: %s", Path(output_path).name)
            return True

        return False

    except subprocess.TimeoutExpired:
        LOGGER.error("FFmpeg fallback timed out for scene")
        return False