import json
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_client import generate, embed

SYSTEM_PREAMBLE = (
    "You are an expert academic content analyzer. "
    "Return only valid JSON with no markdown fences or extra text."
)


def _parse_json_safe(raw: str, prompt: str, retries: int = 1) -> dict | list | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if retries > 0:
            retry_prompt = (
                f"{SYSTEM_PREAMBLE}\n\n"
                "The following output was malformed JSON. Return only valid JSON, nothing else.\n\n"
                f"Original task:\n{prompt}\n\n"
                f"Malformed output to fix:\n{raw}"
            )
            raw2 = generate(retry_prompt)
            return _parse_json_safe(raw2, prompt, retries=0)
        return None


def generate_flashcards(segments: list[dict], outline: list[dict]) -> list[dict]:
    outline_text = "\n".join(
        f"  [{item.get('segment_index', '?')}] {item.get('title', '')} — {item.get('summary_1_sentence', '')}"
        for item in outline
    )
    segments_text = "\n\n".join(
        f"[segment {s['segment_index']} | {s['start_time']:.1f}s] {s['text']}"
        for s in segments
    )
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Generate 15-25 flashcards a student could use to study this lecture.\n"
        "Each flashcard must have:\n"
        '  "front": exam-style question a professor might ask\n'
        '  "back": clear concise answer (2-4 sentences)\n'
        '  "timestamp": start_time in seconds (float) of the segment this came from\n'
        '  "segment_index": integer index of the source segment\n'
        '  "difficulty": one of "easy", "medium", "hard"\n'
        "Return a JSON array of flashcard objects.\n\n"
        f"Lecture outline:\n{outline_text}\n\n"
        f"Transcript segments:\n{segments_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if result is None:
        return []
    return result


def build_search_index(segments: list[dict]) -> list[dict]:
    index = []
    total = len(segments)
    for i, seg in enumerate(segments):
        print(f"Embedding segment {i + 1}/{total}...")
        vector = embed(seg["text"])
        index.append(
            {
                "segment_index": seg["segment_index"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "text": seg["text"],
                "embedding": vector,
            }
        )
    return index


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def semantic_search(query: str, search_index: list[dict], top_k: int = 3) -> list[dict]:
    query_vec = embed(query)
    scored = [
        {
            "segment_index": entry["segment_index"],
            "start_time": entry["start_time"],
            "end_time": entry["end_time"],
            "text": entry["text"],
            "score": _cosine_similarity(query_vec, entry["embedding"]),
        }
        for entry in search_index
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
