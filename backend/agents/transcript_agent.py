import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import GenericProxyConfig

logger = logging.getLogger(__name__)


def _make_api() -> YouTubeTranscriptApi:
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        )
    return YouTubeTranscriptApi()

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


_NO_CAPTIONS_MSG = "This video's captions are not available. Please try a video with captions enabled."


def fetch_transcript_via_youtube_api(video_id: str) -> dict:
    try:
        transcript_list = _make_api().list_transcripts(video_id)
    except Exception as e:
        logger.debug("list_transcripts failed for %s: %s", video_id, e)
        return {"error": "no_captions", "message": _NO_CAPTIONS_MSG}

    transcript = None

    # 1. Manual English
    try:
        transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        logger.info("Found manual English transcript for %s", video_id)
    except Exception:
        pass

    # 2. Auto-generated English
    if transcript is None:
        for t in transcript_list:
            if t.is_generated and t.language_code.startswith("en"):
                transcript = t
                logger.info("Found auto-generated English transcript for %s", video_id)
                break

    # 3. Any transcript translated to English
    if transcript is None:
        for t in transcript_list:
            try:
                transcript = t.translate("en")
                logger.info("Translating %s transcript to English for %s", t.language_code, video_id)
                break
            except Exception:
                continue

    if transcript is None:
        return {"error": "no_captions", "message": _NO_CAPTIONS_MSG}

    try:
        raw = transcript.fetch()
    except Exception as e:
        logger.error("transcript.fetch() failed for %s: %s", video_id, e)
        return {"error": "no_captions", "message": _NO_CAPTIONS_MSG}

    entries = [
        {"start": e["start"], "duration": e.get("duration", 0), "text": e["text"]}
        for e in raw
    ]
    if not entries:
        return {"error": "no_captions", "message": _NO_CAPTIONS_MSG}

    segments = _segment_transcript(entries, SEGMENT_DURATION)
    full_text = " ".join(e["text"] for e in entries)
    duration = entries[-1]["start"] + entries[-1].get("duration", 0)

    logger.info("Fallback transcript succeeded for %s (%d entries)", video_id, len(entries))
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
            fetched = _make_api().fetch(video_id)
            entries = fetched.to_raw_data()
            logger.info("Fetched transcript via youtube-transcript-api (attempt %d)", attempt + 1)
            break
        except VideoUnavailable:
            return {"error": "video_unavailable", "message": "This video is unavailable or private."}
        except TranscriptsDisabled:
            return {"error": "transcripts_disabled", "message": _NO_CAPTIONS_MSG}
        except NoTranscriptFound:
            return {"error": "no_transcript", "message": _NO_CAPTIONS_MSG}
        except Exception as e:
            primary_error = str(e)
            if attempt == 0:
                logger.warning("Primary fetch attempt 1 failed: %s — retrying in 15s", primary_error)
                time.sleep(15)
            else:
                logger.warning("Primary fetch attempt 2 failed: %s", primary_error)

    if entries is None:
        err_lower = (primary_error or "").lower()
        if any(kw in err_lower for kw in ("blocked", "ip", "could not retrieve")):
            logger.info("IP block detected — falling back to list_transcripts for %s", video_id)
            result = fetch_transcript_via_youtube_api(video_id)
            if "error" in result:
                logger.error("Fallback also failed for %s: %s", video_id, result.get("message"))
                return {"error": "all_methods_failed", "message": _NO_CAPTIONS_MSG}
            if use_cache:
                cache_file.write_text(json.dumps(result))
            return result
        return {"error": "fetch_failed", "message": "Could not fetch the transcript. Please try again or use a different video."}

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
