"""
FFmpeg Merger — merge audio+video per scene, then concatenate all into final MP4.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> bool:
    """
    Merge a single video + audio into one clip.
    Re-encodes to ensure consistent codec across all scenes.
    """
    if not Path(video_path).exists():
        LOGGER.error("merge_audio_video: video file missing: %s", video_path)
        return False
    if not Path(audio_path).exists():
        LOGGER.error("merge_audio_video: audio file missing: %s", audio_path)
        return False

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info(
        "Merging: %s + %s → %s",
        Path(video_path).name, Path(audio_path).name, Path(output_path).name,
    )

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-movflags", "+faststart",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        LOGGER.error("FFmpeg merge timed out for %s", Path(output_path).name)
        return False

    if result.returncode != 0:
        LOGGER.error("FFmpeg merge failed (exit %s): %s", result.returncode, result.stderr[-500:])
        return False

    if not Path(output_path).exists():
        LOGGER.error("FFmpeg merge produced no output: %s", output_path)
        return False

    size_kb = Path(output_path).stat().st_size / 1024
    LOGGER.info("Merged clip: %s (%.0f KB)", Path(output_path).name, size_kb)
    return True


def concatenate_videos(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate multiple video clips into final video."""
    # Filter to only existing files
    valid_paths = [p for p in clip_paths if Path(p).exists()]

    if not valid_paths:
        LOGGER.error("concat: no valid clips to concatenate")
        return False

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # If only 1 file, just copy it
    if len(valid_paths) == 1:
        LOGGER.info("Only 1 clip — copying directly to output")
        shutil.copy2(valid_paths[0], output_path)
        return Path(output_path).exists()

    # Create concat list file for FFmpeg
    concat_dir = Path(output_path).parent
    list_file = concat_dir / "concat_list.txt"

    with open(list_file, "w", encoding="utf-8") as f:
        for path in valid_paths:
            abs_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    LOGGER.info("Concatenating %d clips → %s", len(valid_paths), Path(output_path).name)

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        LOGGER.error("FFmpeg concat timed out")
        list_file.unlink(missing_ok=True)
        return False

    # Clean up list file
    list_file.unlink(missing_ok=True)

    if result.returncode != 0:
        LOGGER.error("FFmpeg concat failed (exit %s): %s", result.returncode, result.stderr[-500:])
        return False

    if not Path(output_path).exists():
        LOGGER.error("FFmpeg concat produced no output: %s", output_path)
        return False

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    LOGGER.info("Final video: %s (%.1f MB)", Path(output_path).name, size_mb)
    return True