import json
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_client import generate

logger = logging.getLogger(__name__)

SYSTEM_PREAMBLE = (
    "You are an expert curriculum analyst reviewing university lecture content. "
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


def extract_objectives(learning_objectives: str) -> list:
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Parse the following course learning objectives into a structured list. "
        "Assign each a short ID (O1, O2, ...), extract the objective text, and assign a category "
        "(e.g. 'knowledge', 'skill', 'application', 'analysis', 'synthesis').\n"
        "Return a JSON array:\n"
        '  [{"objective_id": "O1", "objective_text": string, "category": string}]\n\n'
        f"Learning objectives:\n{learning_objectives}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, list):
        logger.warning("extract_objectives returned non-list")
        return []
    return result


def generate_coverage_map(objectives: list, all_transcripts: list[dict]) -> list:
    obj_json = json.dumps(objectives, indent=2)

    transcript_blocks = []
    for t in all_transcripts:
        video_id = t.get("video_id", "unknown")
        title = t.get("title", video_id)
        full_text = (t.get("full_text") or "")[:4000]
        transcript_blocks.append(f"[Video ID: {video_id} | Title: {title}]\n{full_text}")

    transcripts_text = "\n\n---\n\n".join(transcript_blocks)

    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "For each learning objective, determine how well it is covered across the provided lecture transcripts.\n"
        "Coverage levels:\n"
        '  "full"    = objective clearly and thoroughly addressed\n'
        '  "partial" = objective mentioned or only partially addressed\n'
        '  "missing" = objective not covered at all\n'
        "Return a JSON array, one entry per objective, in the same order:\n"
        '  [{"objective_id": string, "coverage": "full"|"partial"|"missing", '
        '"evidence": "brief quote or description (max 2 sentences)", '
        '"video_ids": [string], "timestamps": [string]}]\n\n'
        f"Objectives:\n{obj_json}\n\n"
        f"Lecture Transcripts:\n{transcripts_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, list):
        logger.warning("generate_coverage_map returned non-list")
        return []
    return result


def map_curriculum(all_transcripts: list[dict], learning_objectives: str) -> dict:
    objectives = extract_objectives(learning_objectives)
    coverage_map = generate_coverage_map(objectives, all_transcripts) if objectives else []

    total = len(objectives)
    fully_covered = sum(1 for c in coverage_map if c.get("coverage") == "full")
    partially_covered = sum(1 for c in coverage_map if c.get("coverage") == "partial")
    missing = sum(1 for c in coverage_map if c.get("coverage") == "missing")
    coverage_pct = (
        round((fully_covered + partially_covered * 0.5) / total * 100, 1) if total > 0 else 0.0
    )

    return {
        "objectives": objectives,
        "coverage_map": coverage_map,
        "summary": {
            "total_objectives": total,
            "fully_covered": fully_covered,
            "partially_covered": partially_covered,
            "missing": missing,
            "coverage_percentage": coverage_pct,
        },
    }
