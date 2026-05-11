import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm_client import generate

SYSTEM_PREAMBLE = (
    "You are an expert pedagogical consultant reviewing a university lecture. "
    "Return only valid JSON with no markdown fences or extra text."
)


def _fmt(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


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


def _format_segments(segments: list[dict]) -> str:
    return "\n".join(
        f"[{_fmt(s['start_time'])}] {s['text']}"
        for s in segments
    )


def _call_clarity(segments: list[dict]) -> list:
    seg_text = _format_segments(segments)
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Analyze these lecture transcript segments for clarity and pacing issues.\n"
        "Find the TOP 3 most critical clarity issues only. "
        "Be selective - only include issues that significantly impact student understanding. "
        "Quality over quantity.\n"
        "Look for: confusing explanations, concepts introduced too fast, assumptions of prior knowledge "
        "that weren't established, unclear transitions, or rambling.\n"
        "Return a JSON array of up to 3 objects:\n"
        '  [{"issue": string, "timestamp": "MM:SS", "severity": "high"|"medium"|"low", "suggestion": string}]\n\n'
        f"Segments:\n{seg_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, list):
        return []
    return result[:3]


def _call_accessibility(segments: list[dict]) -> list:
    seg_text = _format_segments(segments)
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Audit these lecture segments for accessibility and equity issues.\n"
        "Find the TOP 3 most critical accessibility issues only. "
        "Be selective - only include the most impactful barriers. "
        "Quality over quantity.\n"
        "Look for: jargon used without definition, examples that assume a specific cultural background or "
        "exclude certain student groups, lack of verbal descriptions for implied visual content, "
        "idiomatic language that non-native speakers may miss.\n"
        "Return a JSON array of up to 3 objects:\n"
        '  [{"issue": string, "timestamp": "MM:SS", "severity": "high"|"medium"|"low", "suggestion": string}]\n\n'
        f"Segments:\n{seg_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, list):
        return []
    return result[:3]


def _call_pedagogical(segments: list[dict], outline: list[dict]) -> dict:
    outline_text = "\n".join(
        f"  [{item.get('segment_index', '?')}] {item.get('title', '')} — {item.get('summary_1_sentence', '')}"
        for item in outline
    )
    seg_text = _format_segments(segments)
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Assess the pedagogical effectiveness of this lecture.\n"
        "Evaluate:\n"
        "  1. Are explicit learning objectives stated near the start?\n"
        "  2. Do concepts build on each other in a logical order? (score 1-10)\n"
        "  3. Are there knowledge checks, questions posed to students, or engagement moments? (score 1-10)\n"
        "Return a JSON object:\n"
        '  {"has_objectives": bool, "logical_flow_score": number, "engagement_score": number, '
        '"strengths": [string], "improvements": [string]}\n\n'
        f"Outline:\n{outline_text}\n\n"
        f"Segments:\n{seg_text}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, dict):
        return {
            "has_objectives": False,
            "logical_flow_score": 5,
            "engagement_score": 5,
            "strengths": [],
            "improvements": [],
        }
    result.setdefault("has_objectives", False)
    result.setdefault("logical_flow_score", 5)
    result.setdefault("engagement_score", 5)
    result.setdefault("strengths", [])
    result.setdefault("improvements", [])
    return result


def _call_priority_fix(
    clarity_issues: list,
    accessibility_issues: list,
    pedagogical: dict,
) -> dict:
    all_issues = json.dumps(
        {
            "clarity_issues": clarity_issues,
            "accessibility_issues": accessibility_issues,
            "pedagogical_assessment": pedagogical,
        },
        indent=2,
    )
    prompt = (
        f"{SYSTEM_PREAMBLE}\n\n"
        "Based on the audit findings below, identify the single most important improvement "
        "a professor should make before publishing or re-delivering this lecture.\n"
        'Return a JSON object:\n'
        '  {"priority_fix": string, "reason": string, "timestamp": "MM:SS", "suggested_rewrite": string}\n\n'
        f"Audit findings:\n{all_issues}"
    )
    raw = generate(prompt)
    result = _parse_json_safe(raw, prompt)
    if not isinstance(result, dict):
        return {
            "priority_fix": "Review overall lecture clarity",
            "reason": "Multiple issues detected across clarity and accessibility dimensions.",
            "timestamp": "0:00",
            "suggested_rewrite": "",
        }
    return result


def _compute_overall_score(
    clarity_issues: list,
    accessibility_issues: list,
    pedagogical: dict,
) -> float:
    flow = pedagogical.get("logical_flow_score", 7)
    engagement = pedagogical.get("engagement_score", 7)
    base_score = (flow + engagement) / 2

    all_issues = clarity_issues + accessibility_issues
    high = sum(1 for i in all_issues if i.get("severity") == "high")
    medium = sum(1 for i in all_issues if i.get("severity") == "medium")
    low = sum(1 for i in all_issues if i.get("severity") == "low")

    raw_penalty = (high * 2 + medium * 1 + low * 0.5) / 16
    penalty = min(raw_penalty * 2.5, 2.5)

    final_score = base_score - penalty
    final_score = max(5.0, min(10.0, final_score))
    return round(final_score, 1)


def audit_lecture(segments: list[dict], outline: list[dict]) -> dict:
    clarity_issues = _call_clarity(segments)
    accessibility_issues = _call_accessibility(segments)
    pedagogical = _call_pedagogical(segments, outline)
    priority_fix = _call_priority_fix(clarity_issues, accessibility_issues, pedagogical)
    overall_score = _compute_overall_score(clarity_issues, accessibility_issues, pedagogical)

    return {
        "clarity_issues": clarity_issues,
        "accessibility_issues": accessibility_issues,
        "pedagogical_assessment": pedagogical,
        "priority_fix": priority_fix,
        "overall_score": overall_score,
    }
