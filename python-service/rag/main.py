from fastapi import FastAPI
from pydantic import BaseModel
from retriever import search_chunks

app = FastAPI()

class QueryRequest(BaseModel):
    question: str
    subject: str | None = None
    class_level: str | None = None
    top_k: int = 3

@app.post("/retrieve")
def retrieve_chunks(req: QueryRequest):
    results = search_chunks(
        query=req.question,
        subject=req.subject,
        class_level=req.class_level,
        top_k = req.top_k
    )
    return {"results": results, "count": len(results)}


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }