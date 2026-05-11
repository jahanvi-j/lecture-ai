"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ParticleCanvas from "@/components/ParticleCanvas";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

/* ── Logo SVG (same as other pages) ── */
function Logo({ size = 24 }: { size?: number }) {
  const h = Math.round(size * (22 / 24));
  return (
    <svg width={size} height={h} viewBox="0 0 56 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="capGP" x1="0" y1="0" x2="56" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#818cf8" />
          <stop offset="100%" stopColor="#c084fc" />
        </linearGradient>
      </defs>
      <polygon points="28,4 50,16 28,28 6,16" fill="url(#capGP)" />
      <path d="M16 22 L16 36 Q28 44 40 36 L40 22 L28 28 Z" fill="url(#capGP)" fillOpacity="0.6" />
      <line x1="50" y1="16" x2="50" y2="30" stroke="#c084fc" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="50" cy="33" r="3" fill="#c084fc" />
      <path d="M31 8 L26 19 L30 19 L25 30 L33 17 L29 17 Z" fill="white" fillOpacity="0.9" />
    </svg>
  );
}

/* ── Header bar ── */
function Header({ onHome }: { onHome: () => void }) {
  return (
    <header className="shrink-0 flex items-center justify-between px-5 py-4 border-b border-zinc-800 bg-[#0f172a]/80 backdrop-blur-sm sticky top-0 z-20">
      <button onClick={onHome} className="text-white text-base font-medium hover:text-zinc-300 transition-colors">
        ← Home
      </button>
      <div className="flex items-center gap-2">
        <Logo size={24} />
        <span className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-violet-400">
          LectureAI
        </span>
      </div>
      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
        Provost Mode
      </span>
    </header>
  );
}

/* ── Agent progress log during loading ── */
type AgentEvent = { agent: string; message: string; done: boolean };

function LoadingScreen({
  events,
  onCancel,
}: {
  events: AgentEvent[];
  onCancel: () => void;
}) {
  return (
    <div className="animated-gradient min-h-screen flex flex-col items-center justify-center relative">
      <ParticleCanvas />
      <div className="relative z-10 flex flex-col items-center gap-8 px-6 max-w-md w-full">
        <div className="relative w-20 h-20">
          <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-[spin-cw_3s_linear_infinite]" />
          <div className="absolute inset-2 rounded-full border-2 border-purple-500/20 animate-[spin-ccw_2s_linear_infinite]" />
          <div className="absolute inset-4 rounded-full border-2 border-violet-500/30 animate-[spin-cw_1.5s_linear_infinite]" />
        </div>
        <div className="text-center">
          <h2 className="text-white text-xl font-semibold mb-1">Mapping Curriculum</h2>
          <p className="text-zinc-400 text-sm">Analyzing lecture coverage against your objectives</p>
        </div>
        <div className="w-full space-y-2">
          {events.map((ev, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className={`shrink-0 w-2 h-2 rounded-full ${ev.done ? "bg-emerald-400" : "bg-indigo-400 animate-pulse"}`} />
              <span className="text-zinc-400 font-medium shrink-0">{ev.agent}</span>
              <span className="text-zinc-500 truncate">{ev.message}</span>
            </div>
          ))}
        </div>
        <button
          onClick={onCancel}
          className="mt-2 px-6 py-2 rounded-lg border border-white/20 text-white text-sm hover:bg-white/10 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ── Coverage badge ── */
function CoverageBadge({ coverage }: { coverage: string }) {
  const styles: Record<string, string> = {
    full: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    partial: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    missing: "bg-red-500/10 border-red-500/30 text-red-400",
  };
  const labels: Record<string, string> = { full: "Full", partial: "Partial", missing: "Missing" };
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[coverage] ?? styles.missing}`}>
      {labels[coverage] ?? coverage}
    </span>
  );
}

/* ── Single objective card ── */
function ObjectiveCard({
  obj,
  coverage,
  videoTitles,
}: {
  obj: { objective_id: string; objective_text: string; category: string };
  coverage: { coverage: string; evidence: string; video_ids: string[]; timestamps: string[] } | undefined;
  videoTitles: string[];
}) {
  const cov = coverage?.coverage ?? "missing";
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">{obj.objective_id}</span>
          <span className="text-xs text-zinc-600 capitalize">{obj.category}</span>
        </div>
        <CoverageBadge coverage={cov} />
      </div>
      <p className="text-white text-sm leading-relaxed">{obj.objective_text}</p>
      {coverage?.evidence && (
        <p className="text-zinc-500 text-xs leading-relaxed italic border-l-2 border-zinc-700 pl-3">
          {coverage.evidence}
        </p>
      )}
      {coverage?.video_ids && coverage.video_ids.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {coverage.video_ids.map((vid, i) => {
            const title = videoTitles.find((_, idx) => idx === i) ?? vid;
            return (
              <span key={vid} className="text-xs text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 rounded px-2 py-0.5">
                {title || vid}
                {coverage.timestamps?.[i] ? ` @ ${coverage.timestamps[i]}` : ""}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Results view ── */
type CurriculumResult = {
  objectives: Array<{ objective_id: string; objective_text: string; category: string }>;
  coverage_map: Array<{ objective_id: string; coverage: string; evidence: string; video_ids: string[]; timestamps: string[] }>;
  video_titles: string[];
  summary: {
    total_objectives: number;
    fully_covered: number;
    partially_covered: number;
    missing: number;
    coverage_percentage: number;
  };
};

function CoverageBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="w-full h-2 rounded-full bg-zinc-800">
      <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function ResultsView({ data, onHome }: { data: CurriculumResult; onHome: () => void }) {
  const { objectives, coverage_map, video_titles, summary } = data;

  const coverageByObj = Object.fromEntries(coverage_map.map((c) => [c.objective_id, c]));

  const groups: Record<string, typeof objectives> = { full: [], partial: [], missing: [] };
  for (const obj of objectives) {
    const cov = coverageByObj[obj.objective_id]?.coverage ?? "missing";
    (groups[cov] ?? groups.missing).push(obj);
  }

  return (
    <div className="min-h-screen bg-[#0f172a] flex flex-col relative">
      <ParticleCanvas />
      <div className="relative z-10 flex flex-col min-h-screen">
        <Header onHome={onHome} />

        <main className="flex-1 overflow-y-auto px-6 py-8 max-w-3xl mx-auto w-full">
          {/* Summary card */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 mb-8 flex flex-col gap-4">
            <h2 className="text-white text-lg font-bold">Coverage Summary</h2>
            <CoverageBar pct={summary.coverage_percentage} />
            <p className="text-zinc-400 text-sm">
              <span className="text-white font-semibold">{summary.coverage_percentage}%</span> of learning objectives covered across{" "}
              <span className="text-white font-semibold">{video_titles.length}</span> lecture(s)
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="text-2xl font-bold text-emerald-400">{summary.fully_covered}</span>
                <span className="text-xs text-emerald-600 font-medium">Fully Covered</span>
              </div>
              <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <span className="text-2xl font-bold text-amber-400">{summary.partially_covered}</span>
                <span className="text-xs text-amber-600 font-medium">Partial</span>
              </div>
              <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                <span className="text-2xl font-bold text-red-400">{summary.missing}</span>
                <span className="text-xs text-red-600 font-medium">Missing</span>
              </div>
            </div>

            {video_titles.length > 0 && (
              <div>
                <p className="text-xs text-zinc-600 uppercase tracking-widest font-semibold mb-2">Lectures Analyzed</p>
                <ul className="space-y-1">
                  {video_titles.map((t, i) => (
                    <li key={i} className="text-zinc-400 text-sm flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs flex items-center justify-center font-bold shrink-0">
                        {i + 1}
                      </span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Objectives by group */}
          {(["full", "partial", "missing"] as const).map((level) => {
            const items = groups[level];
            if (!items.length) return null;
            const headings: Record<string, string> = {
              full: "Fully Covered",
              partial: "Partially Covered",
              missing: "Not Covered",
            };
            return (
              <section key={level} className="mb-8">
                <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-4 flex items-center gap-2">
                  <CoverageBadge coverage={level} />
                  {headings[level]} ({items.length})
                </h3>
                <div className="space-y-4">
                  {items.map((obj) => (
                    <ObjectiveCard
                      key={obj.objective_id}
                      obj={obj}
                      coverage={coverageByObj[obj.objective_id]}
                      videoTitles={video_titles}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </main>

        <footer className="shrink-0 border-t border-zinc-800 px-6 py-4 flex justify-end">
          <p className="text-gray-500 text-sm">LectureAI | Jahanvi Jeswani</p>
        </footer>
      </div>
    </div>
  );
}

/* ── Main page component ── */
export default function ProvostPage() {
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);

  const [phase, setPhase] = useState<"loading" | "results" | "error">("loading");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [result, setResult] = useState<CurriculumResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  function handleHome() {
    abortRef.current?.abort();
    router.push("/");
  }

  function handleCancel() {
    abortRef.current?.abort();
    router.push("/");
  }

  useEffect(() => {
    const urls = JSON.parse(localStorage.getItem("provostUrls") ?? "[]") as string[];
    const objectives = localStorage.getItem("provostObjectives") ?? "";

    if (!urls.length || !objectives.trim()) {
      router.push("/");
      return;
    }

    const ac = new AbortController();
    abortRef.current = ac;

    async function run() {
      try {
        const res = await fetch(`${BACKEND}/api/curriculum/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ urls, learning_objectives: objectives }),
          signal: ac.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`Server error: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (!payload) continue;
            let msg: Record<string, unknown>;
            try {
              msg = JSON.parse(payload);
            } catch {
              continue;
            }
            const ev = msg.event as string;
            if (ev === "agent_start") {
              setEvents((prev) => [
                ...prev,
                { agent: msg.agent as string, message: msg.message as string, done: false },
              ]);
            } else if (ev === "agent_done") {
              setEvents((prev) =>
                prev.map((e) =>
                  e.agent === (msg.agent as string) && !e.done
                    ? { ...e, message: msg.message as string, done: true }
                    : e
                )
              );
            } else if (ev === "error") {
              setErrorMsg((msg.message as string) ?? "An error occurred");
              setPhase("error");
              return;
            } else if (ev === "complete") {
              setResult(msg.data as CurriculumResult);
              setPhase("results");
            }
          }
        }
      } catch (err: unknown) {
        if ((err as { name?: string }).name === "AbortError") return;
        setErrorMsg((err as Error).message ?? "Unknown error");
        setPhase("error");
      }
    }

    run();
    return () => ac.abort();
  }, [router]);

  if (phase === "results" && result) {
    return <ResultsView data={result} onHome={handleHome} />;
  }

  if (phase === "error") {
    return (
      <div className="animated-gradient min-h-screen flex flex-col items-center justify-center gap-6 relative">
        <ParticleCanvas />
        <div className="relative z-10 text-center max-w-md px-6">
          <p className="text-red-400 text-lg font-semibold mb-2">Something went wrong</p>
          <p className="text-zinc-500 text-sm mb-6">{errorMsg}</p>
          <button
            onClick={handleHome}
            className="px-6 py-3 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 transition-colors"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  return <LoadingScreen events={events} onCancel={handleCancel} />;
}
