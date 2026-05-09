import sys
import json
from pathlib import Path

sys.path.insert(0, "backend")

from agents.transcript_agent import fetch_and_segment
from agents.content_agent import analyze_content, format_time
from agents.study_agent import generate_flashcards, build_search_index, semantic_search

TEST_URL = "https://www.youtube.com/watch?v=kCc8FmEb1nY"
_TEST_CACHE = Path("backend/test_data/karpathy_transcript.json")


def test_karpathy():
    print(f"Fetching transcript: {TEST_URL}\n")

    if _TEST_CACHE.exists():
        result = json.loads(_TEST_CACHE.read_text())
        print("Loaded from cache")
    else:
        result = fetch_and_segment(TEST_URL)
        if "error" not in result:
            _TEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _TEST_CACHE.write_text(json.dumps(result))
            print("Fetched from YouTube")

    if "error" in result:
        print(f"ERROR [{result['error']}]: {result['message']}")
        return

    segs = result["segments"]
    print(f"video_id:         {result['video_id']}")
    print(f"duration_seconds: {result['duration_seconds']:.1f}")
    print(f"segment_count:    {len(segs)}")
    print(f"full_text chars:  {len(result['full_text'])}")
    print()

    print("First 3 segments:")
    for seg in segs[:3]:
        preview = seg["text"][:80].replace("\n", " ")
        print(
            f"  [{seg['segment_index']}] {seg['start_time']:.1f}s – {seg['end_time']:.1f}s | {preview}..."
        )

    print("\nLast segment:")
    last = segs[-1]
    preview = last["text"][:80].replace("\n", " ")
    print(f"  [{last['segment_index']}] {last['start_time']:.1f}s – {last['end_time']:.1f}s | {preview}...")

    return segs


def test_error_cases():
    print("\n--- Error case tests ---")

    cases = [
        ("invalid url", "not_a_url"),
        ("youtu.be short", "https://youtu.be/kCc8FmEb1nY"),
        ("shorts url", "https://www.youtube.com/shorts/kCc8FmEb1nY"),
        ("fake private", "https://www.youtube.com/watch?v=XXXXXXXXXXX"),
    ]

    for label, url in cases:
        r = fetch_and_segment(url)
        if "error" in r:
            print(f"  {label}: ERROR [{r['error']}] {r['message']}")
        else:
            print(f"  {label}: OK — {r['video_id']}, {len(r['segments'])} segments")


def test_format_time():
    print("\n--- format_time tests ---")
    cases = [
        (0.0, "0:00"),
        (61.5, "1:01"),
        (3661.0, "1:01:01"),
        (7322.9, "2:02:02"),
    ]
    for secs, expected in cases:
        got = format_time(secs)
        status = "OK" if got == expected else f"FAIL (got {got!r})"
        print(f"  {secs}s → {got!r}  {status}")


def test_content_agent(segments: list[dict]):
    print("\n--- Content agent test (first 5 segments) ---")
    sample = segments[:5]
    print(f"Analyzing {len(sample)} segments ({format_time(sample[0]['start_time'])} – {format_time(sample[-1]['end_time'])})...")

    result = analyze_content(sample)

    print(f"\nOutline ({len(result['outline'])} items):")
    for item in result["outline"]:
        t = format_time(item.get("start_time", 0))
        print(f"  [{t}] {item.get('title', '?')} — {item.get('summary_1_sentence', '')[:80]}...")

    print(f"\nSummaries:")
    for depth in ("short", "medium", "full"):
        text = result["summaries"].get(depth, "")
        print(f"  {depth}: {len(text)} chars | {text[:100].replace(chr(10), ' ')}...")

    print(f"\nKey concepts ({len(result['key_concepts'])}):")
    for c in result["key_concepts"]:
        t = format_time(c.get("start_time", 0))
        print(f"  [{t}] {c.get('term', '?')}: {c.get('definition', '')[:80]}...")

    return result.get("outline", [])


def test_study_agent(segments: list[dict], outline: list[dict]):
    print("\n--- Study agent test ---")

    # Flashcards: first 5 segments
    print("\n[1] Flashcards (first 5 segments)...")
    cards = generate_flashcards(segments[:5], outline)
    print(f"  Generated {len(cards)} flashcards")
    by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
    for c in cards:
        d = c.get("difficulty", "?")
        by_difficulty[d] = by_difficulty.get(d, 0) + 1
    for d, n in by_difficulty.items():
        print(f"    {d}: {n}")
    if cards:
        sample_card = cards[0]
        print(f"\n  Sample card [{sample_card.get('difficulty')} | {format_time(sample_card.get('timestamp', 0))}]:")
        print(f"    Q: {sample_card.get('front', '')}")
        print(f"    A: {sample_card.get('back', '')[:120]}...")

    # Search index: first 3 segments only
    print("\n[2] Building search index (first 3 segments)...")
    index = build_search_index(segments[:3])
    print(f"  Indexed {len(index)} segments, embedding dim: {len(index[0]['embedding']) if index else 0}")

    # Semantic search
    query = "what is tokenization"
    print(f"\n[3] Semantic search: '{query}'")
    results = semantic_search(query, index, top_k=3)
    print(f"  Top {len(results)} results:")
    for r in results:
        t = format_time(r["start_time"])
        print(f"    score={r['score']:.4f} | [{t}] {r['text'][:100].replace(chr(10), ' ')}...")

    print(f"\n  Top result:")
    top = results[0]
    print(f"    segment {top['segment_index']} | {format_time(top['start_time'])} | score={top['score']:.4f}")
    print(f"    {top['text'][:200].replace(chr(10), ' ')}")


if __name__ == "__main__":
    segs = test_karpathy()
    test_error_cases()
    test_format_time()
    outline = []
    if segs:
        outline = test_content_agent(segs)
        test_study_agent(segs, outline)
