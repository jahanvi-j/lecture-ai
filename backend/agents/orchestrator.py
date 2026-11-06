import json
import sys
import os
from typing import Any, TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from agents.transcript_agent import fetch_and_segment
from agents.content_agent import analyze_content
from agents.study_agent import generate_flashcards, build_search_index
from agents.faculty_agent import audit_lecture
from agents.provost_agent import extract_objectives, generate_coverage_map


def _emit(event: str, **kwargs) -> None:
    get_stream_writer()({"event": event, **kwargs})


# ─── Lecture graph (Student / Faculty) ───────────────────────────────────────
#
#   START → transcript ─┬─ error ──────────────────────────────→ END
#                       └─→ content ─┬─→ flashcards ────────────→ END
#                       └─→ search_index ───────────────────────→ END
#                                    └─→ faculty (faculty mode) → END
#
# search_index only needs the transcript, so it runs alongside content;
# flashcards and the faculty audit both wait on the outline and run together.


class LectureState(TypedDict, total=False):
    youtube_url: str
    mode: str
    transcript: dict
    error: dict
    content: dict
    flashcards: list
    search_index: list
    faculty_report: dict


def _transcript_node(state: LectureState) -> dict:
    _emit("agent_start", agent="Transcript Agent", message="Fetching transcript...")
    transcript = fetch_and_segment(state["youtube_url"])
    if "error" in transcript:
        return {"error": transcript}
    _emit("agent_done", agent="Transcript Agent", message=f"Found {len(transcript['segments'])} segments")
    return {"transcript": transcript}


def _content_node(state: LectureState) -> dict:
    _emit("agent_start", agent="Content Agent", message="Building outline and summaries...")
    content = analyze_content(state["transcript"]["segments"])
    _emit("agent_done", agent="Content Agent", message="Outline ready")
    return {"content": content}


def _search_index_node(state: LectureState) -> dict:
    _emit("agent_start", agent="Study Agent", message="Building semantic search index...")
    search_index = build_search_index(state["transcript"]["segments"])
    _emit("agent_done", agent="Study Agent", message="Search index ready")
    return {"search_index": search_index}


def _flashcards_node(state: LectureState) -> dict:
    _emit("agent_start", agent="Study Agent", message="Generating flashcards...")
    flashcards = generate_flashcards(state["transcript"]["segments"], state["content"]["outline"])
    _emit("agent_done", agent="Study Agent", message=f"{len(flashcards)} flashcards ready")
    return {"flashcards": flashcards}


def _faculty_node(state: LectureState) -> dict:
    _emit("agent_start", agent="Faculty Agent", message="Running pedagogical audit...")
    report = audit_lecture(state["transcript"]["segments"], state["content"]["outline"])
    _emit("agent_done", agent="Faculty Agent", message="Audit complete")
    return {"faculty_report": report}


def _route_after_transcript(state: LectureState) -> list[str] | str:
    if state.get("error"):
        return END
    return ["content", "search_index"]


def _route_after_content(state: LectureState) -> list[str]:
    if state.get("mode") == "faculty":
        return ["flashcards", "faculty"]
    return ["flashcards"]


def _build_lecture_graph():
    graph = StateGraph(LectureState)
    graph.add_node("transcript", _transcript_node)
    graph.add_node("content", _content_node)
    graph.add_node("search_index", _search_index_node)
    graph.add_node("flashcards", _flashcards_node)
    graph.add_node("faculty", _faculty_node)

    graph.add_edge(START, "transcript")
    graph.add_conditional_edges("transcript", _route_after_transcript, ["content", "search_index", END])
    graph.add_conditional_edges("content", _route_after_content, ["flashcards", "faculty"])
    graph.add_edge("search_index", END)
    graph.add_edge("flashcards", END)
    graph.add_edge("faculty", END)
    return graph.compile()


lecture_graph = _build_lecture_graph()


def _lecture_result(state: LectureState) -> dict:
    transcript = state["transcript"]
    content = state["content"]
    result = {
        "video_id": transcript["video_id"],
        "duration_seconds": transcript["duration_seconds"],
        "segment_count": len(transcript["segments"]),
        "outline": content["outline"],
        "summaries": content["summaries"],
        "key_concepts": content["key_concepts"],
        "flashcards": state["flashcards"],
        "search_index": state["search_index"],
        "status": "success",
    }
    if "faculty_report" in state:
        result["faculty_report"] = state["faculty_report"]
    return result


def _run_stream(graph, inputs: dict, build_result):
    final_state: dict[str, Any] = {}
    for mode, chunk in graph.stream(inputs, stream_mode=["custom", "values"]):
        if mode == "custom":
            yield json.dumps(chunk)
        else:
            final_state = chunk

    if final_state.get("error"):
        error = final_state["error"]
        yield json.dumps({
            "event": "error",
            "error": error["error"],
            "message": error.get("message", "Transcript fetch failed"),
        })
        return

    yield json.dumps({"event": "complete", "data": build_result(final_state)})


def process_lecture(youtube_url: str, mode: str = "student") -> dict:
    state = lecture_graph.invoke({"youtube_url": youtube_url, "mode": mode})
    if state.get("error"):
        return state["error"]
    return _lecture_result(state)


def process_lecture_stream(youtube_url: str, mode: str = "student"):
    yield from _run_stream(lecture_graph, {"youtube_url": youtube_url, "mode": mode}, _lecture_result)


# ─── Curriculum graph (Provost) ──────────────────────────────────────────────
#
#   START ─┬─→ transcripts ─┬─→ coverage → END
#          └─→ objectives ──┘
#
# Objective extraction only needs the free-text objectives, so it runs while
# the transcripts are being fetched; coverage waits for both.


class CurriculumState(TypedDict, total=False):
    youtube_urls: list[str]
    learning_objectives: str
    transcripts: list[dict]
    objectives: list
    coverage_map: list
    error: dict


def _transcripts_node(state: CurriculumState) -> dict:
    urls = state["youtube_urls"]
    total = len(urls)
    transcripts = []
    for i, url in enumerate(urls, 1):
        _emit("agent_start", agent="Transcript Agent", message=f"Fetching video {i} of {total}...")
        transcript = fetch_and_segment(url)
        if "error" in transcript:
            return {"error": transcript}
        transcripts.append({
            "video_id": transcript["video_id"],
            "title": transcript.get("title", transcript["video_id"]),
            "segments": transcript["segments"],
            "full_text": transcript.get("full_text", " ".join(s["text"] for s in transcript["segments"])),
        })
        _emit("agent_done", agent="Transcript Agent", message=f"Video {i}/{total} ready")
    return {"transcripts": transcripts}


def _objectives_node(state: CurriculumState) -> dict:
    _emit("agent_start", agent="Provost Agent", message="Extracting learning objectives...")
    objectives = extract_objectives(state["learning_objectives"])
    _emit("agent_done", agent="Provost Agent", message=f"Found {len(objectives)} objectives")
    return {"objectives": objectives}


def _coverage_node(state: CurriculumState) -> dict:
    if state.get("error"):
        return {}
    total = len(state["transcripts"])
    _emit("agent_start", agent="Provost Agent", message=f"Mapping coverage across {total} lecture(s)...")
    coverage_map = generate_coverage_map(state["objectives"], state["transcripts"])
    _emit("agent_done", agent="Provost Agent", message="Coverage map complete")
    return {"coverage_map": coverage_map}


def _build_curriculum_graph():
    graph = StateGraph(CurriculumState)
    graph.add_node("transcripts", _transcripts_node)
    graph.add_node("objectives", _objectives_node)
    graph.add_node("coverage", _coverage_node)

    graph.add_edge(START, "transcripts")
    graph.add_edge(START, "objectives")
    graph.add_edge(["transcripts", "objectives"], "coverage")
    graph.add_edge("coverage", END)
    return graph.compile()


curriculum_graph = _build_curriculum_graph()


def _curriculum_result(state: CurriculumState) -> dict:
    objectives = state["objectives"]
    coverage_map = state["coverage_map"]

    fully_covered = sum(1 for c in coverage_map if c.get("coverage") == "full")
    partially_covered = sum(1 for c in coverage_map if c.get("coverage") == "partial")
    missing = sum(1 for c in coverage_map if c.get("coverage") == "missing")
    obj_total = len(objectives)
    coverage_pct = round((fully_covered + partially_covered * 0.5) / obj_total * 100, 1) if obj_total > 0 else 0.0

    return {
        "objectives": objectives,
        "coverage_map": coverage_map,
        "video_titles": [t["title"] for t in state["transcripts"]],
        "summary": {
            "total_objectives": obj_total,
            "fully_covered": fully_covered,
            "partially_covered": partially_covered,
            "missing": missing,
            "coverage_percentage": coverage_pct,
        },
        "status": "success",
    }


def process_curriculum_stream(youtube_urls: list[str], learning_objectives: str):
    yield from _run_stream(
        curriculum_graph,
        {"youtube_urls": youtube_urls, "learning_objectives": learning_objectives},
        _curriculum_result,
    )
