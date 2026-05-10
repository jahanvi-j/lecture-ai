import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_client import generate

SYSTEM_PREAMBLE = (
    "You are an expert academic content analyzer. "
    "Return only valid JSON with no markdown fences or extra text."
)


def format_time(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def _parse_json_safe(raw: str, prompt: str, retries: int = 1) -> dict | list | None:
    text = raw.strip()
    # Strip accidental markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if retries > 0:
            retry_prompt = (
                f"{SYSTEM_PREAMBLE}\n\n"
                f"The following output was malformed JSON. Return only valid JSON, nothing else.\n\n"
                f"Original task:\n{prompt}\n\n"
                f"Malformed output to fix:\n{raw}"
            )
            raw2 = generate(retry_prompt)
            return _parse_json_safe(raw2, prompt, retries=0)
        return None


def _call_outline(segments: list[dict]) -> list:
    segment_lines = "\n".join(
        f"[segment {s['segment_index']} | start_time={s['start_time']:.1f}s] {s['text']}"
        for s in segments
    )
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Given these lecture transcript segments, produce a structured outline.\n"
        "Return a JSON array where each element corresponds to one segment:\n"
        '  {"title": string, "summary_1_sentence": string, "start_time": number, "segment_index": number}\n'
        "start_time must be the exact float value shown after 'start_time=' in the segment header (seconds, not minutes).\n\n"
        f"Segments:\n{segment_lines}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if result is None:
        return [
            {
                "title": f"Segment {s['segment_index']}",
                "summary_1_sentence": s["text"][:120],
                "start_time": s["start_time"],
                "segment_index": s["segment_index"],
            }
            for s in segments
        ]
    # Override start_time with authoritative transcript value — LLM may misinterpret units
    seg_map = {s["segment_index"]: s["start_time"] for s in segments}
    for item in result:
        idx = item.get("segment_index")
        if idx is not None and idx in seg_map:
            item["start_time"] = seg_map[idx]
    return result


def _call_summaries(full_text: str) -> dict:
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Summarize this lecture transcript at three depths.\n"
        "Return a JSON object:\n"
        '  {"short": "3-4 sentence summary for a student with 90 seconds", '
        '"medium": "2-3 paragraph summary for a 5-minute read", '
        '"full": "comprehensive notes covering everything important"}\n\n'
        f"Transcript:\n{full_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if result is None:
        return {
            "short": full_text[:400],
            "medium": full_text[:1200],
            "full": full_text,
        }
    return result


def _call_key_concepts(segments: list[dict], full_text: str) -> list:
    # Build a start_time lookup keyed on approximate position for the LLM hint
    segment_hints = "\n".join(
        f"  {s['start_time']:.1f}s: {s['text'][:60]}"
        for s in segments
    )
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Extract 5-10 key concepts or terms from this lecture.\n"
        "For start_time, use the number of seconds (float) when the concept first appears.\n"
        "Return a JSON array:\n"
        '  [{"term": string, "definition": string, "start_time": number}]\n\n'
        f"Segment timestamps for reference:\n{segment_hints}\n\n"
        f"Full transcript:\n{full_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if result is None:
        return []
    return result


def analyze_content(segments: list[dict]) -> dict:
    full_text = " ".join(s["text"] for s in segments)

    outline = _call_outline(segments)
    summaries = _call_summaries(full_text)
    key_concepts = _call_key_concepts(segments, full_text)

    return {
        "outline": outline,
        "summaries": summaries,
        "key_concepts": key_concepts,
    }
