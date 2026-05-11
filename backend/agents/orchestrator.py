import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.transcript_agent import fetch_and_segment
from agents.content_agent import analyze_content
from agents.study_agent import generate_flashcards, build_search_index
from agents.faculty_agent import audit_lecture
from agents.provost_agent import extract_objectives, generate_coverage_map
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

    if mode == "faculty":
        result["faculty_report"] = audit_lecture(segments, outline)

    return result


def process_lecture_stream(youtube_url: str, mode: str = "student"):
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

    if mode == "faculty":
        yield _event("agent_start", agent="Faculty Agent", message="Running pedagogical audit...")
        result["faculty_report"] = audit_lecture(segments, outline)
        yield _event("agent_done", agent="Faculty Agent", message="Audit complete")

    yield _event("complete", data=result)


def process_curriculum_stream(youtube_urls: list[str], learning_objectives: str):
    def _event(event: str, **kwargs) -> str:
        return json.dumps({"event": event, **kwargs})

    all_transcripts = []
    total = len(youtube_urls)

    for i, url in enumerate(youtube_urls, 1):
        yield _event("agent_start", agent="Transcript Agent", message=f"Fetching video {i} of {total}...")
        transcript = fetch_and_segment(url)
        if "error" in transcript:
            yield _event("error", error=transcript["error"], message=transcript.get("message", "Transcript fetch failed"))
            return
        all_transcripts.append({
            "video_id": transcript["video_id"],
            "title": transcript.get("title", transcript["video_id"]),
            "segments": transcript["segments"],
            "full_text": transcript.get("full_text", " ".join(s["text"] for s in transcript["segments"])),
        })
        yield _event("agent_done", agent="Transcript Agent", message=f"Video {i}/{total} ready")

    yield _event("agent_start", agent="Provost Agent", message="Extracting learning objectives...")
    objectives = extract_objectives(learning_objectives)
    yield _event("agent_done", agent="Provost Agent", message=f"Found {len(objectives)} objectives")

    yield _event("agent_start", agent="Provost Agent", message=f"Mapping coverage across {total} lecture(s)...")
    coverage_map = generate_coverage_map(objectives, all_transcripts)
    yield _event("agent_done", agent="Provost Agent", message="Coverage map complete")

    fully_covered = sum(1 for c in coverage_map if c.get("coverage") == "full")
    partially_covered = sum(1 for c in coverage_map if c.get("coverage") == "partial")
    missing = sum(1 for c in coverage_map if c.get("coverage") == "missing")
    obj_total = len(objectives)
    coverage_pct = round((fully_covered + partially_covered * 0.5) / obj_total * 100, 1) if obj_total > 0 else 0.0

    result = {
        "objectives": objectives,
        "coverage_map": coverage_map,
        "video_titles": [t["title"] for t in all_transcripts],
        "summary": {
            "total_objectives": obj_total,
            "fully_covered": fully_covered,
            "partially_covered": partially_covered,
            "missing": missing,
            "coverage_percentage": coverage_pct,
        },
        "status": "success",
    }

    yield _event("complete", data=result)
