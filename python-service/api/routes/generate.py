import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from rag.retriever import search_chunks, detect_subject
from rag.llm_generator import generate_answer_and_script
from video.validator import extract_scenes_from_script

LOGGER = logging.getLogger(__name__)
router = APIRouter()

# Map tab names / abbreviations → what Qdrant actually stores
SUBJECT_ALIASES = {
    "mathgpt": "science",
    "math": "science",
    "maths": "science",
    "mathematics": "science",
    "physicsgpt": "science",
    "physics": "science",
    "chemgpt": "science",
    "chem": "science",
    "chemistry": "science",
    "biogpt": "science",
    "biology": "science",
    "bio": "science",
    "sciencegpt": "science",
}


def _normalize_subject(raw: str) -> str:
    """Map frontend tab names to Qdrant subject values."""
    key = raw.strip().lower()
    return SUBJECT_ALIASES.get(key, key)


class GenerateRequest(BaseModel):
    question: str
    board: str = "CBSE"
    class_level: str = "7"
    subject: str = "auto"   # "auto" | "physics" | "chemistry" | "mathematics"
    top_k: int = 5


class GenerateResponse(BaseModel):
    answer: str
    citations: list
    scenes: list
    raw_llm: dict
    detected_subject: str = "general"


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # Auto-detect subject from question if "auto" or use provided
    detected_subject = detect_subject(req.question)
    subject = _normalize_subject(req.subject) if req.subject != "auto" else _normalize_subject(detected_subject)
    LOGGER.info("Generate: q=%s, subject=%s (raw=%s), class=%s",
                req.question[:60], subject, req.subject, req.class_level)

    # STEP 1: RAG retrieval with the normalized subject
    chunks = search_chunks(
        query=req.question,
        subject=subject,
        class_level=req.class_level,
        top_k=req.top_k,
    )

    # Fallback 1: relax subject filter
    if not chunks:
        LOGGER.warning("No chunks with subject=%s, trying without subject filter", subject)
        chunks = search_chunks(
            query=req.question,
            subject=None,
            class_level=req.class_level,
            top_k=req.top_k,
        )

    # Fallback 2: relax all filters (just semantic search)
    if not chunks:
        LOGGER.warning("No chunks with class=%s, trying pure semantic search", req.class_level)
        chunks = search_chunks(
            query=req.question,
            subject=None,
            class_level=None,
            top_k=req.top_k,
        )

    if not chunks:
        LOGGER.warning(
            "No NCERT chunks found for '%s'. AI will answer from its own knowledge.",
            req.question[:60],
        )
        chunks = []  # LLM will use its own knowledge
    else:
        LOGGER.info("Found %d chunks (best score=%.3f)", len(chunks), chunks[0].get("score", 0))

    # STEP 2: LLM generation
    try:
        llm_output = await generate_answer_and_script(
            question=req.question,
            chunks=chunks,
            board=req.board,
            class_level=req.class_level,
            subject=req.subject,
        )
    except Exception as e:
        LOGGER.error("LLM error: %s", e)
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # Step 3: Validate Manim scenes
    scenes = extract_scenes_from_script(llm_output)

    # Build answer — fallback to scenes narration if LLM didn't provide an answer
    answer = llm_output.get("answer", "")
    if not answer and scenes:
        answer = "\n\n".join(
            s.get("narration", "") for s in scenes if s.get("narration")
        )

    # Build citations from RAG chunks if LLM didn't provide them
    citations = llm_output.get("citations", [])
    if not citations and chunks:
        citations = [
            {
                "source": f"Class {c.get('class', 'N/A')} {c.get('subject', 'N/A')}",
                "chapter": c.get("chapter", "N/A"),
            }
            for c in chunks[:3]
        ]

    return GenerateResponse(
        answer=answer,
        citations=citations,
        scenes=scenes,
        raw_llm=llm_output,
        detected_subject=llm_output.get("detected_subject", detected_subject),
    )
