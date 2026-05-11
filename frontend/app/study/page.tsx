"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { translateContent } from "../../lib/api";
import ParticleCanvas from "@/components/ParticleCanvas";

// ─── Types ───────────────────────────────────────────────────────────────────

interface OutlineItem {
  title: string;
  summary_1_sentence: string;
  start_time: number;
  segment_index: number;
}

interface Summaries {
  short: string;
  medium: string;
  full: string;
}

interface KeyConcept {
  term: string;
  definition: string;
  start_time: number;
}

interface Flashcard {
  front: string;
  back: string;
  timestamp: number;
  segment_index: number;
  difficulty: "easy" | "medium" | "hard";
}

interface SearchIndexEntry {
  segment_index: number;
  start_time: number;
  end_time: number;
  text: string;
  embedding: number[];
}

interface SearchResult {
  segment_index: number;
  start_time: number;
  end_time: number;
  text: string;
  score: number;
}

interface AuditIssue {
  issue: string;
  timestamp: string;
  severity: "high" | "medium" | "low";
  suggestion: string;
}

interface PedagogicalAssessment {
  has_objectives: boolean;
  logical_flow_score: number;
  engagement_score: number;
  strengths: string[];
  improvements: string[];
}

interface PriorityFix {
  priority_fix: string;
  reason: string;
  timestamp: string;
  suggested_rewrite: string;
}

interface FacultyReport {
  clarity_issues: AuditIssue[];
  accessibility_issues: AuditIssue[];
  pedagogical_assessment: PedagogicalAssessment;
  priority_fix: PriorityFix;
  overall_score: number;
}

interface LectureResult {
  video_id: string;
  duration_seconds: number;
  segment_count: number;
  outline: OutlineItem[];
  summaries: Summaries;
  key_concepts: KeyConcept[];
  flashcards: Flashcard[];
  search_index: SearchIndexEntry[];
  status: string;
  faculty_report?: FacultyReport;
}

interface ProgressEvent {
  event: string;
  agent?: string;
  message?: string;
  error?: string;
  done?: boolean;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseTimestamp(ts: string): number {
  const parts = ts.split(":").map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  // single token — treat as raw seconds (LLM may return "840" instead of "14:00")
  if (parts.length === 1 && !isNaN(parts[0])) return parts[0];
  return 0;
}

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0)
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function TimestampPill({
  seconds,
  onSeek,
}: {
  seconds: number;
  onSeek: (s: number) => void;
}) {
  return (
    <button
      onClick={() => onSeek(seconds)}
      className="inline-flex items-center px-2.5 py-1 rounded-md bg-indigo-600 text-white text-xs font-mono font-medium hover:bg-indigo-500 hover:scale-105 transition-all cursor-pointer shrink-0"
    >
      {formatTime(seconds)}
    </button>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function ProgressFeed({ events }: { events: ProgressEvent[] }) {
  return (
    <div className="font-mono text-base space-y-2">
      {events.map((ev, i) => {
        const isDone = ev.event === "agent_done";
        return (
          <div key={i} className="fade-in flex items-start gap-3">
            <span
              className={`mt-0.5 text-base leading-none ${
                isDone ? "text-green-400" : "text-indigo-400 dot-pulse"
              }`}
            >
              ●
            </span>
            <span className={isDone ? "text-zinc-300" : "text-zinc-400"}>
              <span className="text-white font-semibold">{ev.agent}</span>
              {ev.message ? ` — ${ev.message}` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function OutlineTab({
  outline,
  onSeek,
}: {
  outline: OutlineItem[];
  onSeek: (s: number) => void;
}) {
  return (
    <div className="space-y-3">
      {outline.map((item, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-4 rounded-xl bg-[#1a1a1a] border border-zinc-800 hover:border-zinc-700 transition-colors"
        >
          <TimestampPill seconds={item.start_time} onSeek={onSeek} />
          <div className="min-w-0">
            <p className="text-white font-medium text-lg leading-snug">
              {item.title}
            </p>
            <p className="text-zinc-500 text-base mt-1 leading-relaxed">
              {item.summary_1_sentence}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function SummariesTab({ summaries }: { summaries: Summaries }) {
  type Depth = "short" | "medium" | "full";
  const [depth, setDepth] = useState<Depth>("short");

  const labels: { key: Depth; label: string }[] = [
    { key: "short", label: "90 sec" },
    { key: "medium", label: "5 min" },
    { key: "full", label: "Full Notes" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {labels.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setDepth(key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              depth === key
                ? "bg-indigo-600 text-white"
                : "bg-[#1a1a1a] text-zinc-400 border border-zinc-800 hover:border-zinc-600"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="p-4 rounded-xl bg-[#1a1a1a] border border-zinc-800">
        <p className="text-zinc-300 text-base leading-relaxed whitespace-pre-wrap">
          {summaries[depth]}
        </p>
      </div>
    </div>
  );
}

function FlashcardsTab({
  flashcards,
  onSeek,
}: {
  flashcards: Flashcard[];
  onSeek: (s: number) => void;
}) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const card = flashcards[index];
  if (!card) return null;

  const difficultyColor = {
    easy: "bg-emerald-900 text-emerald-300",
    medium: "bg-amber-900 text-amber-300",
    hard: "bg-red-900 text-red-300",
  };

  const difficultyBorder = {
    easy: "border-emerald-700",
    medium: "border-amber-600",
    hard: "border-red-700",
  };

  function go(dir: 1 | -1) {
    setFlipped(false);
    setTimeout(() => setIndex((i) => Math.max(0, Math.min(flashcards.length - 1, i + dir))), 150);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-zinc-500 text-sm">
        <span>
          Card {index + 1} of {flashcards.length}
        </span>
        <span className="text-xs text-zinc-600">Click card to flip</span>
      </div>

      <div className="flip-card w-full" style={{ height: "260px" }}>
        <div
          className={`flip-card-inner w-full h-full cursor-pointer ${
            flipped ? "flipped" : ""
          }`}
          onClick={() => setFlipped((f) => !f)}
        >
          {/* Front */}
          <div className={`flip-card-front p-6 rounded-xl bg-[#1a1a1a] border-2 ${difficultyBorder[card.difficulty] ?? difficultyBorder.medium} flex flex-col justify-between`}>
            <div className="flex items-start justify-between gap-3">
              <p className="text-white text-lg font-medium leading-relaxed">
                {card.front}
              </p>
              <span
                className={`shrink-0 text-xs px-2 py-1 rounded-md font-medium capitalize ${
                  difficultyColor[card.difficulty] ?? difficultyColor.medium
                }`}
              >
                {card.difficulty}
              </span>
            </div>
            <p className="text-zinc-600 text-xs mt-4">Tap to reveal answer →</p>
          </div>

          {/* Back */}
          <div className="flip-card-back p-6 rounded-xl bg-[#1e1a2e] border border-indigo-900 flex flex-col justify-between">
            <p className="text-zinc-200 text-base leading-relaxed">{card.back}</p>
            <div className="flex items-center gap-2 mt-4">
              <span className="text-zinc-600 text-xs">From:</span>
              <TimestampPill seconds={card.timestamp} onSeek={onSeek} />
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => go(-1)}
          disabled={index === 0}
          className="flex-1 py-3 rounded-xl bg-[#1a1a1a] border border-zinc-800 text-zinc-400 text-sm font-medium disabled:opacity-30 hover:border-zinc-600 transition-colors"
        >
          ← Previous
        </button>
        <button
          onClick={() => go(1)}
          disabled={index === flashcards.length - 1}
          className="flex-1 py-3 rounded-xl bg-[#1a1a1a] border border-zinc-800 text-zinc-400 text-sm font-medium disabled:opacity-30 hover:border-zinc-600 transition-colors"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

function SearchTab({
  searchIndex,
  onSeek,
}: {
  searchIndex: SearchIndexEntry[];
  onSeek: (s: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, search_index: searchIndex }),
      });
      const data = await res.json();
      setResults(data.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything about this lecture..."
          className="flex-1 rounded-xl bg-[#1a1a1a] border border-zinc-800 text-white placeholder-zinc-600 px-4 py-3 text-sm focus:outline-none focus:border-zinc-500 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-3 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 transition-colors"
        >
          {loading ? "…" : "Search"}
        </button>
      </form>

      {loading && (
        <div className="text-zinc-500 text-sm text-center py-6">
          Searching...
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-zinc-500 text-sm text-center py-6">
          No results found.
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-[#1a1a1a] border border-zinc-800 space-y-2"
            >
              <div className="flex items-center gap-2">
                <TimestampPill seconds={r.start_time} onSeek={onSeek} />
                <span className="text-zinc-500 text-xs">
                  Score: {(r.score * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-zinc-300 text-base leading-relaxed line-clamp-3">
                {r.text}
              </p>
              <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, r.score * 100).toFixed(1)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Results Layout ──────────────────────────────────────────────────────

type Tab = "outline" | "summaries" | "flashcards" | "search";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "hi", label: "Hindi" },
  { code: "zh", label: "Chinese" },
  { code: "ar", label: "Arabic" },
];

const DEFAULT_SPLIT = 40;
const MIN_LEFT = 25;
const MAX_LEFT = 70;

function ResultsView({
  result,
  mode,
}: {
  result: LectureResult;
  mode: string;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("outline");
  const [language, setLanguage] = useState("en");
  const [translating, setTranslating] = useState(false);
  const [displayResult, setDisplayResult] = useState<LectureResult>(result);
  const [leftWidth, setLeftWidth] = useState(DEFAULT_SPLIT);
  const originalRef = useRef<LectureResult>(result);
  const playerRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const splitRef = useRef(DEFAULT_SPLIT);

  useEffect(() => {
    const saved = localStorage.getItem("splitPos");
    if (saved) {
      const v = parseFloat(saved);
      setLeftWidth(v);
      splitRef.current = v;
    }
  }, []);

  function onDividerMouseDown(e: React.MouseEvent) {
    e.preventDefault();
    const onMouseMove = (ev: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((ev.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(MAX_LEFT, Math.max(MIN_LEFT, pct));
      splitRef.current = clamped;
      setLeftWidth(clamped);
    };
    const onMouseUp = () => {
      localStorage.setItem("splitPos", String(splitRef.current));
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }

  function onDividerDblClick() {
    setLeftWidth(DEFAULT_SPLIT);
    splitRef.current = DEFAULT_SPLIT;
    localStorage.setItem("splitPos", String(DEFAULT_SPLIT));
  }

  async function handleLanguageChange(lang: string) {
    setLanguage(lang);
    if (lang === "en") {
      setDisplayResult(originalRef.current);
      return;
    }
    setTranslating(true);
    try {
      const content = {
        outline: originalRef.current.outline,
        summaries: originalRef.current.summaries,
        flashcards: originalRef.current.flashcards,
        key_concepts: originalRef.current.key_concepts,
      };
      const translated = await translateContent(content, lang);
      setDisplayResult((prev) => ({
        ...prev,
        outline: translated.outline ?? prev.outline,
        summaries: translated.summaries ?? prev.summaries,
        flashcards: translated.flashcards ?? prev.flashcards,
        key_concepts: translated.key_concepts ?? prev.key_concepts,
      }));
    } catch {
      setLanguage("en");
      setDisplayResult(originalRef.current);
    } finally {
      setTranslating(false);
    }
  }

  function seekTo(seconds: number) {
    playerRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: "command", func: "seekTo", args: [seconds, true] }),
      "https://www.youtube.com"
    );
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "outline", label: "Outline", icon: "📋" },
    { key: "summaries", label: "Summaries", icon: "📝" },
    { key: "flashcards", label: "Flashcards", icon: "🃏" },
    { key: "search", label: "Search", icon: "🔍" },
  ];

  return (
    <div className="bg-[#0f172a] flex flex-col h-screen overflow-hidden relative">
      <ParticleCanvas />
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-900/80 shrink-0 z-20 bg-[#08101e]/90 backdrop-blur-sm">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 text-white text-base font-medium hover:text-zinc-300 transition-colors"
        >
          ← Home
        </button>
        <div className="flex items-center gap-2">
          <svg width="24" height="22" viewBox="0 0 56 52" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="hCapG" x1="0" y1="0" x2="56" y2="52" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#818cf8"/>
                <stop offset="100%" stopColor="#c084fc"/>
              </linearGradient>
            </defs>
            <polygon points="28,4 50,16 28,28 6,16" fill="url(#hCapG)"/>
            <path d="M16 22 L16 36 Q28 44 40 36 L40 22 L28 28 Z" fill="url(#hCapG)" fillOpacity="0.6"/>
            <line x1="50" y1="16" x2="50" y2="30" stroke="#c084fc" strokeWidth="2.5" strokeLinecap="round"/>
            <circle cx="50" cy="33" r="3" fill="#c084fc"/>
            <path d="M31 8 L26 19 L30 19 L25 30 L33 17 L29 17 Z" fill="white" fillOpacity="0.9"/>
          </svg>
          <span className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-violet-400">LectureAI</span>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
          mode === "faculty"
            ? "bg-amber-950 border-amber-800 text-amber-300"
            : "bg-indigo-950 border-indigo-800 text-indigo-300"
        }`}>
          {mode === "faculty" ? "Faculty Mode" : "Student Mode"}
        </span>
      </div>
      {/* Split panel */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
      {/* Left — video + concepts */}
      <div
        style={{ width: `${leftWidth}%` }}
        className="flex flex-col overflow-y-auto border-r border-zinc-900 p-5 gap-5 shrink-0"
      >
        <div className="rounded-xl overflow-hidden bg-black aspect-video">
          <iframe
            ref={playerRef}
            id="yt-player"
            title="Lecture video player"
            src={`https://www.youtube.com/embed/${result.video_id}?enablejsapi=1`}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>

        <div>
          <p className="text-zinc-500 text-xs font-semibold uppercase tracking-wider mb-2">
            Key Concepts
          </p>
          <div className="flex flex-wrap gap-2">
            {displayResult.key_concepts.map((c, i) => (
              <button
                key={i}
                onClick={() => seekTo(c.start_time)}
                title={c.definition}
                className="px-3 py-1.5 rounded-lg bg-[#1a1a1a] border border-zinc-800 text-zinc-300 text-sm hover:border-indigo-700 hover:text-indigo-300 hover:shadow-[0_0_10px_rgba(99,102,241,0.4)] transition-all text-left"
              >
                {c.term}
                <span className="ml-1.5 text-zinc-600 font-mono">
                  {formatTime(c.start_time)}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="text-zinc-700 text-sm font-mono">
          {result.segment_count} segments · {formatTime(result.duration_seconds)}
        </div>
      </div>

      {/* Drag divider */}
      <div
        onMouseDown={onDividerMouseDown}
        onDoubleClick={onDividerDblClick}
        title="Drag to resize · Double-click to reset"
        className="w-2 bg-zinc-900 hover:bg-indigo-900 cursor-col-resize flex items-center justify-center shrink-0 transition-all select-none group"
      >
        <span className="text-zinc-600 group-hover:text-indigo-300 text-base leading-none select-none transition-colors group-hover:drop-shadow-[0_0_6px_rgba(99,102,241,0.8)]">
          ⟺
        </span>
      </div>

      {/* Right — tabs */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab bar */}
        <div className="flex items-center border-b border-zinc-900 shrink-0">
          <div className="flex">
            {tabs.map(({ key, label, icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                title={label}
                className={`px-6 py-3 text-base font-medium transition-colors relative flex items-center gap-2 ${
                  tab === key
                    ? "text-white"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <span>{icon}</span>
                <span>{label}</span>
                {tab === key && (
                  <span className="absolute bottom-0 left-0 right-0 h-[3px] bg-indigo-500 rounded-t" />
                )}
              </button>
            ))}
          </div>

          <div className="ml-auto pr-4 flex items-center gap-2">
            {translating && (
              <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            )}
            <select
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              disabled={translating}
              className="bg-[#1a1a1a] text-white text-sm border border-zinc-700 rounded-lg px-3 py-2.5 focus:outline-none focus:border-indigo-500 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === "outline" && (
            <OutlineTab outline={displayResult.outline} onSeek={seekTo} />
          )}
          {tab === "summaries" && (
            <SummariesTab summaries={displayResult.summaries} />
          )}
          {tab === "flashcards" && (
            <FlashcardsTab flashcards={displayResult.flashcards} onSeek={seekTo} />
          )}
          {tab === "search" && (
            <SearchTab searchIndex={result.search_index} onSeek={seekTo} />
          )}
        </div>
      </div>
      </div>
      <div className="shrink-0 px-5 py-3 text-right border-t border-zinc-900/50">
        <p className="text-gray-500 text-sm">LectureAI | Jahanvi Jeswani</p>
      </div>
    </div>
  );
}

// ─── Faculty Results View ────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: "high" | "medium" | "low" }) {
  const styles = {
    high: "bg-red-900 text-red-300 border-red-800",
    medium: "bg-amber-900 text-amber-300 border-amber-800",
    low: "bg-blue-900 text-blue-300 border-blue-800",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-md font-medium border capitalize ${styles[severity]}`}>
      {severity}
    </span>
  );
}

function ScoreCircle({ label, score }: { label: string; score: number }) {
  const color =
    score >= 8 ? "text-emerald-400 border-emerald-700" :
    score >= 6 ? "text-amber-400 border-amber-700" :
    "text-red-400 border-red-700";
  return (
    <div className={`flex flex-col items-center justify-center w-28 h-28 rounded-full border-2 ${color}`}>
      <span className="text-2xl font-bold">{score}</span>
      <span className="text-xs opacity-70 mt-0.5">/10</span>
      <span className="text-xs mt-1 opacity-80">{label}</span>
    </div>
  );
}

function IssueCard({
  issue,
  onSeek,
}: {
  issue: AuditIssue;
  onSeek: (s: number) => void;
}) {
  return (
    <div className="p-4 rounded-xl bg-[#1a1a1a] border border-zinc-800 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <SeverityBadge severity={issue.severity} />
        <TimestampPill seconds={parseTimestamp(issue.timestamp)} onSeek={onSeek} />
      </div>
      <p className="text-white text-sm leading-relaxed">{issue.issue}</p>
      <p className="text-zinc-500 text-xs leading-relaxed">{issue.suggestion}</p>
    </div>
  );
}

function FacultyResultsView({ result }: { result: LectureResult; mode?: string }) {
  const router = useRouter();
  const report = result.faculty_report!;
  const playerRef = useRef<HTMLIFrameElement>(null);

  function seekTo(seconds: number) {
    playerRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: "command", func: "seekTo", args: [seconds, true] }),
      "https://www.youtube.com"
    );
  }

  const scoreColor =
    report.overall_score >= 8 ? "text-emerald-400" :
    report.overall_score >= 6 ? "text-amber-400" :
    "text-red-400";

  const ped = report.pedagogical_assessment;

  return (
    <div className="min-h-screen bg-[#0f172a] relative overflow-y-auto">
      <ParticleCanvas />
      {/* Top bar */}
      <div className="sticky top-0 z-20 flex items-center justify-between px-5 py-4 border-b border-zinc-900/80 bg-[#08101e]/90 backdrop-blur-sm">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-1.5 text-white text-base font-medium hover:text-zinc-300 transition-colors"
        >
          ← Home
        </button>
        <div className="flex items-center gap-2">
          <svg width="24" height="22" viewBox="0 0 56 52" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="fCapG" x1="0" y1="0" x2="56" y2="52" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#818cf8"/>
                <stop offset="100%" stopColor="#c084fc"/>
              </linearGradient>
            </defs>
            <polygon points="28,4 50,16 28,28 6,16" fill="url(#fCapG)"/>
            <path d="M16 22 L16 36 Q28 44 40 36 L40 22 L28 28 Z" fill="url(#fCapG)" fillOpacity="0.6"/>
            <line x1="50" y1="16" x2="50" y2="30" stroke="#c084fc" strokeWidth="2.5" strokeLinecap="round"/>
            <circle cx="50" cy="33" r="3" fill="#c084fc"/>
            <path d="M31 8 L26 19 L30 19 L25 30 L33 17 L29 17 Z" fill="white" fillOpacity="0.9"/>
          </svg>
          <span className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-violet-400">LectureAI</span>
        </div>
        <span className="px-2.5 py-1 rounded-full text-xs font-medium border bg-amber-950 border-amber-800 text-amber-300">
          Faculty Mode
        </span>
      </div>
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* Video — small, centered */}
        <div className="flex justify-center">
          <div className="w-full max-w-[400px] rounded-xl overflow-hidden bg-black aspect-video">
            <iframe
              ref={playerRef}
              title="Lecture video player"
              src={`https://www.youtube.com/embed/${result.video_id}?enablejsapi=1`}
              className="w-full h-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </div>

        {/* Section 1 — Overall Score */}
        <div className="text-center space-y-1">
          <p className={`text-6xl font-bold ${scoreColor}`}>
            {report.overall_score}
            <span className="text-3xl text-zinc-500"> / 10</span>
          </p>
          <p className="text-zinc-400 text-sm uppercase tracking-widest font-semibold">
            Lecture Quality Score
          </p>
        </div>

        {/* Section 2 — Priority Fix */}
        <div className="rounded-2xl border border-orange-800 bg-[#1a0f00] p-6 space-y-4">
          <p className="text-orange-400 font-bold text-lg">⚡ Top Priority Fix</p>
          <p className="text-white text-xl font-semibold leading-snug">
            {report.priority_fix.priority_fix}
          </p>
          <p className="text-zinc-400 text-sm leading-relaxed">{report.priority_fix.reason}</p>
          <div className="flex items-center gap-2">
            <span className="text-zinc-500 text-xs">At:</span>
            <TimestampPill
              seconds={parseTimestamp(report.priority_fix.timestamp)}
              onSeek={seekTo}
            />
          </div>
          {report.priority_fix.suggested_rewrite && (
            <div className="mt-2 p-4 rounded-xl bg-[#0f0f0f] border border-zinc-800">
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 font-semibold">
                Suggested Rewrite
              </p>
              <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap font-mono">
                {report.priority_fix.suggested_rewrite}
              </p>
            </div>
          )}
        </div>

        {/* Section 3 — Issues Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">
              Clarity Issues
            </p>
            {report.clarity_issues.length === 0 ? (
              <p className="text-zinc-600 text-sm">No clarity issues found.</p>
            ) : (
              report.clarity_issues.map((issue, i) => (
                <IssueCard key={i} issue={issue} onSeek={seekTo} />
              ))
            )}
          </div>

          <div className="space-y-3">
            <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">
              Accessibility Issues
            </p>
            {report.accessibility_issues.length === 0 ? (
              <p className="text-zinc-600 text-sm">No accessibility issues found.</p>
            ) : (
              report.accessibility_issues.map((issue, i) => (
                <IssueCard key={i} issue={issue} onSeek={seekTo} />
              ))
            )}
          </div>
        </div>

        {/* Section 4 — Pedagogical Assessment */}
        <div className="rounded-2xl bg-[#1a1a1a] border border-zinc-800 p-6 space-y-6">
          <p className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">
            Pedagogical Assessment
          </p>

          <div className="flex flex-wrap items-center gap-6">
            <ScoreCircle label="Flow" score={ped.logical_flow_score} />
            <ScoreCircle label="Engagement" score={ped.engagement_score} />
            <div className="flex items-center gap-2">
              {ped.has_objectives ? (
                <span className="text-emerald-400 text-xl">✓</span>
              ) : (
                <span className="text-red-400 text-xl">✗</span>
              )}
              <span className="text-zinc-300 text-sm">
                Learning objectives {ped.has_objectives ? "stated" : "not stated"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {ped.strengths.length > 0 && (
              <div>
                <p className="text-emerald-500 text-xs font-semibold uppercase tracking-wider mb-2">
                  Strengths
                </p>
                <ul className="space-y-1.5">
                  {ped.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <span className="text-emerald-500 mt-0.5 shrink-0">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {ped.improvements.length > 0 && (
              <div>
                <p className="text-orange-400 text-xs font-semibold uppercase tracking-wider mb-2">
                  Improvements
                </p>
                <ul className="space-y-1.5">
                  {ped.improvements.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <span className="text-orange-400 mt-0.5 shrink-0">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <p className="text-right text-gray-500 text-sm py-4">LectureAI | Jahanvi Jeswani</p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

function StudyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const videoUrl = searchParams.get("url") ?? "";
  const mode = searchParams.get("mode") ?? "student";

  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<LectureResult | null>(null);
  const [error, setError] = useState("");
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!videoUrl) {
      setError("No URL provided.");
      return;
    }

    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stream?url=${encodeURIComponent(videoUrl)}&mode=${mode}`
    );

    es.onmessage = (e) => {
      const parsed = JSON.parse(e.data) as {
        event: string;
        agent?: string;
        message?: string;
        error?: string;
        data?: LectureResult;
      };

      if (parsed.event === "complete") {
        setResult(parsed.data!);
        es.close();
      } else if (parsed.event === "error") {
        setError(parsed.message ?? "An error occurred.");
        es.close();
      } else {
        setEvents((prev) => [
          ...prev,
          {
            event: parsed.event,
            agent: parsed.agent,
            message: parsed.message,
            done: parsed.event === "agent_done",
          },
        ]);
      }
    };

    es.onerror = () => {
      setError("Cannot connect to backend. Is the server running?");
      es.close();
    };

    return () => es.close();
  }, [videoUrl]);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events]);

  if (result) {
    if (mode === "faculty" && result.faculty_report) return <FacultyResultsView result={result} mode={mode} />;
    return <ResultsView result={result} mode={mode} />;
  }

  if (error) {
    return (
      <main className="animated-gradient min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md p-6 rounded-2xl bg-[#1a1a1a] border border-red-900 space-y-4">
          <p className="text-red-400 font-semibold">Error</p>
          <p className="text-zinc-400 text-sm">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="w-full py-3 rounded-xl bg-white text-black text-sm font-semibold hover:bg-zinc-200 transition-colors"
          >
            ← Back to Home
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="animated-gradient min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      <ParticleCanvas />

      <div className="w-full max-w-2xl space-y-8 relative z-10">
        {/* Concentric rings */}
        <div className="flex justify-center">
          <div className="relative w-20 h-20 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-indigo-500/20" style={{ animation: "spin-cw 6s linear infinite" }} />
            <div className="absolute inset-2 rounded-full border border-indigo-400/30" style={{ animation: "spin-ccw 4s linear infinite" }} />
            <div className="absolute inset-4 rounded-full border-t border-indigo-400" style={{ animation: "spin-cw 2s linear infinite" }} />
            <span className="text-indigo-400 text-xl relative z-10">⚡</span>
          </div>
        </div>

        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white">
            Analyzing your lecture...
          </h1>
          <p className="text-zinc-500 text-sm font-mono truncate">{videoUrl}</p>
        </div>

        <div
          ref={feedRef}
          className="p-5 rounded-2xl bg-[#1a1a1a]/80 border border-zinc-800 backdrop-blur-sm max-h-72 overflow-y-auto space-y-2"
        >
          {events.length === 0 ? (
            <p className="text-zinc-600 text-base font-mono">Connecting...</p>
          ) : (
            <ProgressFeed events={events} />
          )}
        </div>

        <button
          onClick={() => router.push("/")}
          className="w-full py-3 rounded-xl text-white text-sm font-medium border border-white/20 hover:border-white/40 hover:bg-white/5 transition-all"
        >
          ✕ Cancel
        </button>
      </div>
    </main>
  );
}

export default function StudyPage() {
  return (
    <Suspense
      fallback={
        <main className="animated-gradient min-h-screen flex items-center justify-center">
          <p className="text-zinc-600 font-mono text-sm">Loading...</p>
        </main>
      }
    >
      <StudyContent />
    </Suspense>
  );
}
