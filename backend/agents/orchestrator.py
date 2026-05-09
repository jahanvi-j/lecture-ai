import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.transcript_agent import fetch_and_segment
from agents.content_agent import analyze_content
from agents.study_agent import generate_flashcards, build_search_index
from llm_client import generate


def process_lecture(youtube_url: str, mode: str = "student") -> dict:
    transcript = fetch_and_segment(youtube_url)
    if "error" in transcript:
        return transcript

    segments = transcript["segments"]

    content = analyze_content(segments)
    outline = content["outline"]

    flashcards = generate_flashcards(segments, outline)
    search_index = build_search_index(segments)

    return {
        "video_id": transcript["video_id"],
        "duration_seconds": transcript["duration_seconds"],
        "segment_count": len(segments),
        "outline": outline,
        "summaries": content["summaries"],
        "key_concepts": content["key_concepts"],
        "flashcards": flashcards,
        "search_index": search_index,
        "status": "success",
    }


def process_lecture_stream(youtube_url: str):
    def _event(event: str, **kwargs) -> str:
        return json.dumps({"event": event, **kwargs})

    yield _event("agent_start", agent="Transcript Agent", message="Fetching transcript...")
    transcript = fetch_and_segment(youtube_url)
    if "error" in transcript:
        yield _event("error", error=transcript["error"], message=transcript["message"])
        return
    segments = transcript["segments"]
    yield _event("agent_done", agent="Transcript Agent", message=f"Found {len(segments)} segments")

    yield _event("agent_start", agent="Content Agent", message="Building outline and summaries...")
    content = analyze_content(segments)
    outline = content["outline"]
    yield _event("agent_done", agent="Content Agent", message="Outline ready")

    yield _event("agent_start", agent="Study Agent", message="Generating flashcards...")
    flashcards = generate_flashcards(segments, outline)
    yield _event("agent_done", agent="Study Agent", message=f"{len(flashcards)} flashcards ready")

    yield _event("agent_start", agent="Study Agent", message="Building semantic search index...")
    search_index = build_search_index(segments)
    yield _event("agent_done", agent="Study Agent", message="Search index ready")

    result = {
        "video_id": transcript["video_id"],
        "duration_seconds": transcript["duration_seconds"],
        "segment_count": len(segments),
        "outline": outline,
        "summaries": content["summaries"],
        "key_concepts": content["key_concepts"],
        "flashcards": flashcards,
        "search_index": search_index,
        "status": "success",
    }
    yield _event("complete", data=result)
