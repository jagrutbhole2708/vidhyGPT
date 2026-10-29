import logging
import uuid
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from video.job_worker import create_job, get_job, process_video_job

LOGGER = logging.getLogger(__name__)
router = APIRouter()


class VideoRequest(BaseModel):
    topic: str
    answer_context: str  # the RAG answer text — keeps video consistent
    subject: str
    class_level: str
    board: str = "CBSE"
    job_id: str | None = None  # optional: Next.js can pass its own job ID


@router.post("/video/create")
async def create_video(req: VideoRequest, background_tasks: BackgroundTasks):
    job_id = req.job_id or str(uuid.uuid4())
    create_job(job_id)

    LOGGER.info("Video job created: %s (topic=%s)", job_id[:8], req.topic[:50])

    # Fire and forget — runs in background
    background_tasks.add_task(
        process_video_job,
        job_id=job_id,
        topic=req.topic,
        answer_context=req.answer_context,
        subject=req.subject,
        class_level=req.class_level,
        board=req.board,
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/video/status/{job_id}")
def get_video_status(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="JOB NOT FOUND")

    return job
