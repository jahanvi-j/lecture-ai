import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import process_lecture, process_lecture_stream, process_curriculum_stream
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


class CurriculumRequest(BaseModel):
    urls: list[str]
    learning_objectives: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/process")
def process(req: ProcessRequest):
    return process_lecture(req.url, mode=req.mode)


@app.get("/api/stream")
def stream(url: str = Query(...), mode: str = Query("student")):
    def sse_generator():
        for line in process_lecture_stream(url, mode=mode):
            yield f"data: {line}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/curriculum/stream")
def curriculum_stream(req: CurriculumRequest):
    def sse_generator():
        for line in process_curriculum_stream(req.urls, req.learning_objectives):
            yield f"data: {line}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/search")
def search(req: SearchRequest):
    results = semantic_search(req.query, req.search_index, top_k=3)
    return {"results": results}


@app.post("/api/translate")
def translate(req: TranslateRequest):
    import json

    content = req.content
    language = req.language

    outline_json = json.dumps(content.get("outline", []), ensure_ascii=False)
    summaries_json = json.dumps(content.get("summaries", {}), ensure_ascii=False)
    flashcards_json = json.dumps(content.get("flashcards", []), ensure_ascii=False)

    prompt = (
        f"Translate the following lecture content to {language}.\n"
        "Return ONLY valid JSON. No markdown. No backticks. No explanation.\n"
        "Just the raw JSON object with the same structure as input.\n"
        "Preserve all JSON keys exactly. Only translate the string values.\n"
        "Keep all numeric fields, timestamps, and segment_index values unchanged.\n"
        "Use actual unicode characters for all scripts including Chinese, Arabic, Hindi"
        " — do not use escape sequences.\n\n"
        "Return a JSON object with keys: outline, summaries, flashcards.\n\n"
        f"outline: {outline_json}\n\n"
        f"summaries: {summaries_json}\n\n"
        f"flashcards: {flashcards_json}"
    )

    def _try_parse(raw: str) -> dict | None:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except Exception:
            return None

    translated = None
    for attempt in range(3):
        raw = generate(prompt)
        translated = _try_parse(raw)
        if translated is not None:
            break

    if translated is None:
        return {**content}

    return {
        **content,
        "outline": translated.get("outline", content.get("outline")),
        "summaries": translated.get("summaries", content.get("summaries")),
        "flashcards": translated.get("flashcards", content.get("flashcards")),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
