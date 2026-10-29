import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes.generate import router as generate_router
from api.routes.video import router as video_router
# from api.routes.quiz import router as quiz_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

app = FastAPI(title="VidhyaGPT PYTHON SERVICE")

frontend_url = os.getenv("FRONTEND_URL")
origins = [
    "http://localhost:3000",
]
if frontend_url:
    origins.extend([url.strip() for url in frontend_url.split(",") if url.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)
app.include_router(video_router)
# app.include_router(quiz_router)

# Serve rendered videos as static files
videos_dir = Path("outputs/videos")
videos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(videos_dir)), name="videos")


@app.get("/health")
def health_check():
    return {"status": "ok"}