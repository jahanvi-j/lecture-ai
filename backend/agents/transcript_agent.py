import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

_api = YouTubeTranscriptApi()

SEGMENT_DURATION = 120  # seconds
_CACHE_DIR = Path(__file__).parent.parent / "cache"


def _extract_video_id(url: str) -> str | None:
    url = url.strip()

    short = re.match(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if short:
        return short.group(1)

    parsed = urlparse(url)

    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            ids = qs.get("v")
            if ids:
                return ids[0]
        shorts = re.match(r"/shorts/([a-zA-Z0-9_-]{11})", parsed.path)
        if shorts:
            return shorts.group(1)
        embed = re.match(r"/embed/([a-zA-Z0-9_-]{11})", parsed.path)
        if embed:
            return embed.group(1)

    return None


def _segment_transcript(entries: list[dict], segment_duration: int) -> list[dict]:
    segments = []
    current_texts = []
    current_start = entries[0]["start"] if entries else 0.0
    segment_index = 0

    for entry in entries:
        start = entry["start"]

        if start - current_start >= segment_duration and current_texts:
            segments.append(
                {
                    "text": " ".join(current_texts).strip(),
                    "start_time": current_start,
                    "end_time": start,
                    "segment_index": segment_index,
                }
            )
            current_texts = []
            current_start = start
            segment_index += 1

        current_texts.append(entry["text"])

    if current_texts:
        last = entries[-1]
        segments.append(
            {
                "text": " ".join(current_texts).strip(),
                "start_time": current_start,
                "end_time": last["start"] + last.get("duration", 0),
                "segment_index": segment_index,
            }
        )

    return segments


def fetch_and_segment(youtube_url: str, use_cache: bool = True) -> dict:
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return {"error": "invalid_url", "message": f"Could not extract video ID from: {youtube_url}"}

    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"{video_id}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

    try:
        fetched = _api.fetch(video_id)
        entries = fetched.to_raw_data()
    except VideoUnavailable:
        return {"error": "video_unavailable", "message": f"Video {video_id} is unavailable or private"}
    except TranscriptsDisabled:
        return {"error": "transcripts_disabled", "message": f"Transcripts are disabled for video {video_id}"}
    except NoTranscriptFound:
        return {"error": "no_transcript", "message": f"No transcript found for video {video_id}"}
    except Exception as e:
        return {"error": "fetch_failed", "message": str(e)}

    if not entries:
        return {"error": "empty_transcript", "message": f"Transcript for {video_id} is empty"}

    segments = _segment_transcript(entries, SEGMENT_DURATION)
    full_text = " ".join(e["text"] for e in entries)
    duration = entries[-1]["start"] + entries[-1].get("duration", 0)

    result = {
        "video_id": video_id,
        "segments": segments,
        "full_text": full_text,
        "duration_seconds": duration,
    }

    if use_cache:
        cache_file.write_text(json.dumps(result))

    return result
