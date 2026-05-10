import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

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


def fetch_transcript_via_youtube_api(video_id: str) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return {"error": "no_api_key", "message": "YOUTUBE_API_KEY not configured"}

    with httpx.Client(timeout=30) as client:
        # List caption tracks to confirm English availability
        cap_resp = client.get(
            "https://www.googleapis.com/youtube/v3/captions",
            params={"part": "snippet", "videoId": video_id, "key": api_key},
        )
        if cap_resp.status_code == 200:
            items = cap_resp.json().get("items", [])
            has_english = any(
                item.get("snippet", {}).get("language", "").startswith("en")
                for item in items
            )
            if items and not has_english:
                logger.warning("No English caption track listed for %s via Data API", video_id)

        # Timedtext works for both manual and auto-generated captions on public videos
        tt_resp = client.get(
            "https://www.youtube.com/api/timedtext",
            params={"lang": "en", "v": video_id, "fmt": "json3"},
        )
        if tt_resp.status_code != 200:
            return {
                "error": "timedtext_failed",
                "message": f"Timedtext endpoint returned HTTP {tt_resp.status_code}",
            }

        try:
            tt_data = tt_resp.json()
        except Exception:
            return {"error": "timedtext_parse_error", "message": "Failed to parse timedtext response"}

        entries = []
        for event in tt_data.get("events", []):
            text = "".join(s.get("utf8", "") for s in event.get("segs", [])).strip()
            if text:
                entries.append({
                    "start": event.get("tStartMs", 0) / 1000.0,
                    "duration": event.get("dDurationMs", 0) / 1000.0,
                    "text": text,
                })

        if not entries:
            return {"error": "empty_transcript", "message": f"No text content in timedtext for {video_id}"}

        segments = _segment_transcript(entries, SEGMENT_DURATION)
        full_text = " ".join(e["text"] for e in entries)
        duration = entries[-1]["start"] + entries[-1].get("duration", 0)

        logger.info("YouTube Data API fallback succeeded for %s (%d entries)", video_id, len(entries))
        return {
            "video_id": video_id,
            "segments": segments,
            "full_text": full_text,
            "duration_seconds": duration,
        }


def fetch_and_segment(youtube_url: str, use_cache: bool = True) -> dict:
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return {"error": "invalid_url", "message": f"Could not extract video ID from: {youtube_url}"}

    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"{video_id}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

    entries = None
    primary_error = None

    for attempt in range(2):
        try:
            fetched = _api.fetch(video_id)
            entries = fetched.to_raw_data()
            logger.info("Fetched transcript via youtube-transcript-api (attempt %d)", attempt + 1)
            break
        except VideoUnavailable:
            return {"error": "video_unavailable", "message": f"Video {video_id} is unavailable or private"}
        except TranscriptsDisabled:
            return {"error": "transcripts_disabled", "message": f"Transcripts are disabled for video {video_id}"}
        except NoTranscriptFound:
            return {"error": "no_transcript", "message": f"No transcript found for video {video_id}"}
        except Exception as e:
            primary_error = str(e)
            if attempt == 0:
                logger.warning("Primary fetch attempt 1 failed: %s — retrying in 5s", primary_error)
                time.sleep(5)
            else:
                logger.warning("Primary fetch attempt 2 failed: %s", primary_error)

    if entries is None:
        err_lower = (primary_error or "").lower()
        if any(kw in err_lower for kw in ("blocked", "ip", "could not retrieve")):
            logger.info("IP block detected — falling back to YouTube Data API for %s", video_id)
            result = fetch_transcript_via_youtube_api(video_id)
            if "error" in result:
                logger.error("YouTube Data API fallback failed: %s", result.get("message"))
                return {"error": "all_methods_failed", "message": f"Primary: {primary_error} | API: {result.get('message')}"}
            if use_cache:
                cache_file.write_text(json.dumps(result))
            return result
        return {"error": "fetch_failed", "message": primary_error}

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
