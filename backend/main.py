import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import process_lecture, process_lecture_stream
from agents.study_agent import semantic_search
from llm_client import generate

app = FastAPI(title="Lecture AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    url: str
    mode: str = "student"


class SearchRequest(BaseModel):
    query: str
    search_index: list


class TranslateRequest(BaseModel):
    content: dict
    language: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/process")
def process(req: ProcessRequest):
    return process_lecture(req.url, mode=req.mode)


@app.get("/api/stream")
def stream(url: str = Query(...)):
    def sse_generator():
        for line in process_lecture_stream(url):
            yield f"data: {line}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/search")
def search(req: SearchRequest):
    results = semantic_search(req.query, req.search_index, top_k=3)
    return {"results": results}


@app.post("/api/translate")
def translate(req: TranslateRequest):
    content = req.content
    language = req.language

    outline_json = str(content.get("outline", []))
    summaries_json = str(content.get("summaries", {}))
    flashcards_json = str(content.get("flashcards", []))

    prompt = (
        "You are an expert academic translator. Return only valid JSON with no markdown fences.\n\n"
        f"Translate the following lecture content to {language}. "
        "Translate all human-readable text fields (titles, summaries, questions, answers, definitions). "
        "Keep all numeric fields, timestamps, and segment_index values unchanged.\n\n"
        "Return a JSON object with keys: outline, summaries, flashcards.\n\n"
        f"outline: {outline_json}\n\n"
        f"summaries: {summaries_json}\n\n"
        f"flashcards: {flashcards_json}"
    )

    import json

    raw = generate(prompt)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        translated = json.loads(text)
    except Exception:
        return {"error": "translation_failed", "raw": raw}

    return {
        **content,
        "outline": translated.get("outline", content.get("outline")),
        "summaries": translated.get("summaries", content.get("summaries")),
        "flashcards": translated.get("flashcards", content.get("flashcards")),
    }
