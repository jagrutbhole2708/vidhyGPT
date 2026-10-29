"""
Job Worker — orchestrates the full video generation pipeline.

Pipeline Order (CRITICAL):
1. Generate script JSON (5 scenes with narration + visual_content)
2. Generate TTS audio for EVERY scene → get exact duration
3. Generate Manim code for each scene (AFTER audio, so duration is known)
4. Render each Manim scene to MP4 (720p 30fps)
5. Merge audio + video per scene
6. Concatenate all merged clips into final MP4
7. Save to: outputs/videos/{job_id}.mp4

NO S3 upload — just local file save.
"""

import logging
import os
import shutil
import tempfile
import httpx
from datetime import datetime
from pathlib import Path

from video.script_generator import generate_script, clean_topic_title
from video.manim_code_generator import generate_manim_code
from video.tts_engine import generate_audio
from video.manim_renderer import render_scene, render_fallback_ffmpeg
from video.ffmpeg_merger import merge_audio_video, concatenate_videos

LOGGER = logging.getLogger(__name__)

# ── In-memory job store ──
_jobs: dict[str, dict] = {}

VIDEO_OUTPUT_DIR = Path(os.getenv("VIDEO_OUTPUT_DIR", "./outputs/videos"))
VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_job(job_id: str):
    _jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "video_url": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs):
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)

async def _send_webhook(job_id: str, status: str, video_url: str | None = None, error: str | None = None):
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        LOGGER.info("No WEBHOOK_URL configured, skipping webhook.")
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                webhook_url,
                json={
                    "jobId": job_id,
                    "status": status,
                    "videoUrl": video_url,
                    "error": error,
                },
                timeout=10.0
            )
            resp.raise_for_status()
            LOGGER.info("[%s] Webhook sent successfully: %s", job_id[:8], status)
    except Exception as e:
        LOGGER.error("[%s] Failed to send webhook: %s", job_id[:8], e)


async def process_video_job(
    job_id: str,
    topic: str,
    answer_context: str,
    subject: str,
    class_level: str,
    board: str = "CBSE",
):
    """
    Main pipeline — runs as FastAPI BackgroundTask or standalone.
    Follows the exact pipeline order specified.
    """
    tag = job_id[:8]
    update_job(job_id, status="processing", progress=5)
    job_dir = Path(tempfile.mkdtemp(prefix=f"job_{tag}_"))

    try:
        # ══════════════════════════════════════════════════════
        # STEP 0: Clean the topic title (question → clean title)
        # ══════════════════════════════════════════════════════
        clean_title = clean_topic_title(topic)
        LOGGER.info("[%s] Cleaned topic: '%s' → '%s'", tag, topic[:40], clean_title)

        # ══════════════════════════════════════════════════════
        # STEP 1 (progress 5→15): Generate script
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 1: Generating script...", tag)
        script = await generate_script(clean_title, answer_context, subject, class_level)
        scenes = script.get("scenes", [])
        title = script.get("title", topic)

        if not scenes:
            raise ValueError("Script generation returned no scenes")

        LOGGER.info("[%s] Got %d scenes: %s", tag, len(scenes), title)

        # DEBUG: dump full script to see what LLM returned
        import json as _json_debug
        LOGGER.info("[%s] SCRIPT DUMP:\n%s", tag, _json_debug.dumps(script, indent=2, ensure_ascii=False)[:3000])

        for i, s in enumerate(scenes):
            vc = s.get("visual_content", {})
            vc_keys = list(vc.keys()) if isinstance(vc, dict) else []
            LOGGER.info("  Scene %d: [%s] %s | visual_content_keys=%s",
                        i + 1, s.get("scene_type"), s.get("title"), vc_keys)
        update_job(job_id, progress=15)

        # ══════════════════════════════════════════════════════
        # STEP 2 (progress 15→35): Generate TTS audio for EVERY scene
        # Audio MUST come before Manim so we know exact durations
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 2: Generating audio for all scenes...", tag)
        audio_data = []  # list of {"path": str, "duration": float}

        for i, scene in enumerate(scenes):
            audio_path = str(job_dir / f"audio_{i + 1}.mp3")
            duration = generate_audio(scene["narration"], audio_path)
            audio_data.append({"path": audio_path, "duration": duration})
            LOGGER.info("  Scene %d audio: %.1fs → %s", i + 1, duration, Path(audio_path).name)
            update_job(job_id, progress=15 + int((i + 1) / len(scenes) * 20))

        total_audio = sum(a["duration"] for a in audio_data)
        LOGGER.info("[%s] Total audio duration: %.1fs", tag, total_audio)
        update_job(job_id, progress=35)

        # ══════════════════════════════════════════════════════
        # STEP 3 (progress 35→55): Generate Manim code (duration known)
        # Now passes visual_content from script JSON directly
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 3: Generating Manim code for all scenes...", tag)
        manim_codes = []

        for i, scene in enumerate(scenes):
            vc = scene.get("visual_content") or {}
            LOGGER.info("  Generating scene %d: type=%s, visual_content_keys=%s",
                        i + 1, scene.get("scene_type"), list(vc.keys()) if isinstance(vc, dict) else [])

            code = await generate_manim_code(
                scene_number=i + 1,
                scene_title=scene.get("title", ""),
                narration=scene.get("narration", ""),
                visual_content=vc,
                duration=audio_data[i]["duration"],
                topic=clean_title,
                subject=subject,
                scene_type=scene.get("scene_type", "bullets"),
            )
            manim_codes.append(code)
            LOGGER.info("  Scene %d Manim code: %d chars", i + 1, len(code))
            update_job(job_id, progress=35 + int((i + 1) / len(scenes) * 20))

        # DEBUG: dump code preview for each scene
        for i, code in enumerate(manim_codes):
            LOGGER.info("--- Scene %d code preview (first 300 chars) ---\n%s\n---",
                        i + 1, code[:300])

        update_job(job_id, progress=55)

        # ══════════════════════════════════════════════════════
        # STEP 4 (progress 55→80): Render Manim scenes to MP4
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 4: Rendering Manim scenes...", tag)
        video_files = []

        for i, code in enumerate(manim_codes):
            video_path = str(job_dir / f"scene_{i + 1}.mp4")
            class_name = f"Scene{i + 1}"

            success = render_scene(
                manim_code=code,
                scene_class_name=class_name,
                output_path=video_path,
                duration_seconds=audio_data[i]["duration"],
                scene_index=i + 1,
            )

            if not success or not Path(video_path).exists():
                # Use FFmpeg fallback with scene title (not narration — that's audio)
                LOGGER.warning("  Scene %d render failed → FFmpeg fallback", i + 1)
                render_fallback_ffmpeg(
                    text=scenes[i].get("title", scenes[i]["narration"][:80]),
                    output_path=video_path,
                    duration=audio_data[i]["duration"],
                )

            video_files.append(video_path)
            LOGGER.info("  Scene %d/%d rendered", i + 1, len(scenes))
            update_job(job_id, progress=55 + int((i + 1) / len(scenes) * 25))

        update_job(job_id, progress=80)

        # ══════════════════════════════════════════════════════
        # STEP 5 (progress 80→90): Merge audio + video per scene
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 5: Merging audio + video per scene...", tag)
        merged_clips = []

        for i in range(len(scenes)):
            merged_path = str(job_dir / f"merged_{i + 1}.mp4")
            ok = merge_audio_video(video_files[i], audio_data[i]["path"], merged_path)

            if ok and Path(merged_path).exists():
                merged_clips.append(merged_path)
            else:
                LOGGER.warning("  Scene %d merge failed → using video only", i + 1)
                merged_clips.append(video_files[i])

        update_job(job_id, progress=90)

        # ══════════════════════════════════════════════════════
        # STEP 6 (progress 90→100): Concatenate into final MP4
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 6: Concatenating all clips into final video...", tag)
        final_path = str(VIDEO_OUTPUT_DIR / f"{job_id}.mp4")

        ok = concatenate_videos(merged_clips, final_path)
        if not ok or not Path(final_path).exists():
            raise ValueError("Final concatenation failed — no output file")

        size_mb = Path(final_path).stat().st_size / (1024 * 1024)
        LOGGER.info("[%s] Final video: %.1f MB → %s", tag, size_mb, final_path)

        # ══════════════════════════════════════════════════════
        # STEP 7 (progress 95→100): Upload to S3
        # ══════════════════════════════════════════════════════
        LOGGER.info("[%s] Step 7: Uploading to S3...", tag)
        update_job(job_id, progress=95)

        try:
            from video.s3_uploader import upload_video_to_s3
            video_url = upload_video_to_s3(final_path, job_id)
            if video_url:
                LOGGER.info("[%s] ✅ Uploaded to S3: %s", tag, video_url)
            else:
                # S3 upload returned None — fall back to local
                LOGGER.warning("[%s] S3 upload returned None, using local URL", tag)
                base = os.getenv("PYTHON_SERVICE_URL", "http://localhost:8000")
                video_url = f"{base}/videos/{job_id}.mp4"
        except Exception as e:
            # S3 upload failed — fall back to local file URL
            LOGGER.warning("[%s] S3 upload failed (%s), using local URL", tag, e)
            base = os.getenv("PYTHON_SERVICE_URL", "http://localhost:8000")
            video_url = f"{base}/videos/{job_id}.mp4"

        LOGGER.info("[%s] ✅ Final video ready: %s", tag, video_url)

        update_job(
            job_id,
            status="done",
            progress=100,
            video_url=video_url,
        )
        
        await _send_webhook(job_id, "done", video_url=video_url)

    except Exception as e:
        import traceback
        LOGGER.error("[%s] ❌ FAILED: %s", tag, e)
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))
        await _send_webhook(job_id, "failed", error=str(e))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
