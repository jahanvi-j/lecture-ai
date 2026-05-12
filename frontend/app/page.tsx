"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ParticleCanvas from "@/components/ParticleCanvas";

type Mode = "student" | "faculty" | "provost";

const FEATURES = [
  {
    icon: "📋",
    title: "Smart Outlines",
    desc: "Timestamped chapters you can jump to",
  },
  {
    icon: "🔍",
    title: "Semantic Search",
    desc: "Find any moment by asking a question",
  },
  {
    icon: "🎓",
    title: "Faculty Audit",
    desc: "Private teaching quality report",
  },
  {
    icon: "🗺️",
    title: "Curriculum Map",
    desc: "See which objectives your course actually covers",
  },
];

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<Mode>("student");
  const [error, setError] = useState("");
  const [provostUrls, setProvostUrls] = useState(["", "", ""]);
  const [objectives, setObjectives] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (mode === "provost") {
      const filled = provostUrls.map((u) => u.trim()).filter(Boolean);
      if (filled.length === 0) {
        setError("Enter at least one YouTube URL.");
        return;
      }
      if (!objectives.trim()) {
        setError("Enter learning objectives.");
        return;
      }
      localStorage.setItem("provostUrls", JSON.stringify(filled));
      localStorage.setItem("provostObjectives", objectives.trim());
      router.push("/provost");
      return;
    }

    if (!url.trim()) {
      setError("Please enter a YouTube URL.");
      return;
    }
    localStorage.setItem("lectureUrl", url.trim());
    localStorage.setItem("lectureMode", mode);
    router.push(`/study?url=${encodeURIComponent(url.trim())}&mode=${mode}`);
  }

  return (
    <>
      <ParticleCanvas />
      <main className="animated-gradient min-h-screen flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-xl flex flex-col items-center gap-8">
          <div className="flex flex-col items-center gap-3 text-center">
            {/* Logo */}
            <svg width="56" height="52" viewBox="0 0 56 52" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="capG" x1="0" y1="0" x2="56" y2="52" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#818cf8"/>
                  <stop offset="100%" stopColor="#c084fc"/>
                </linearGradient>
              </defs>
              <polygon points="28,4 50,16 28,28 6,16" fill="url(#capG)"/>
              <path d="M16 22 L16 36 Q28 44 40 36 L40 22 L28 28 Z" fill="url(#capG)" fillOpacity="0.6"/>
              <line x1="50" y1="16" x2="50" y2="30" stroke="#c084fc" strokeWidth="2.5" strokeLinecap="round"/>
              <circle cx="50" cy="33" r="3" fill="#c084fc"/>
              <path d="M31 8 L26 19 L30 19 L25 30 L33 17 L29 17 Z" fill="white" fillOpacity="0.9"/>
            </svg>

            <h1 className="text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-violet-400">
              LectureAI
            </h1>
            <p className="text-zinc-400 text-lg">
              Turn any lecture into a complete study environment
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {["⚡ 5 AI Agents", "🌍 6 Languages", "🎓 Student + Faculty + Provost"].map((badge) => (
                <span
                  key={badge}
                  className="px-3 py-1 rounded-full text-xs font-medium bg-zinc-900 border border-zinc-700 text-zinc-400"
                >
                  {badge}
                </span>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
            {/* Mode selector */}
            <div className="flex flex-col gap-1">
              <div className="flex gap-2">
                {(
                  [
                    { m: "student" as Mode, tip: "Turn any lecture into flashcards, summaries & search" },
                    { m: "faculty" as Mode, tip: "Get a private teaching quality audit with fixes" },
                    { m: "provost" as Mode, tip: "Map multiple lectures against course objectives" },
                  ] as { m: Mode; tip: string }[]
                ).map(({ m, tip }) => (
                  <button
                    key={m}
                    type="button"
                    title={tip}
                    onClick={() => { setMode(m); setError(""); }}
                    className={`flex-1 py-3 rounded-xl text-sm font-medium capitalize transition-colors ${
                      mode === m
                        ? "bg-white text-black"
                        : "bg-[#1a1a1a] text-zinc-400 border border-zinc-800 hover:border-zinc-600"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
              {mode === "faculty" && (
                <p className="text-gray-500 text-xs text-center mt-1">
                  🔒 Your audit report is private — only you see the results
                </p>
              )}
              {mode === "provost" && (
                <p className="text-gray-500 text-xs text-center mt-1">
                  Paste URLs from the same course to map curriculum coverage
                </p>
              )}
            </div>

            {mode !== "provost" ? (
              <div className="flex flex-col gap-1">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (error) setError("");
                  }}
                  placeholder="Paste a YouTube URL..."
                  className="w-full rounded-xl bg-[#1a1a1a] border border-zinc-800 text-white placeholder-zinc-600 px-5 py-4 text-base focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
                <p className="text-gray-500 text-xs mt-1 text-center">
                  Video must be public and have captions enabled
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-zinc-500 text-xs uppercase tracking-widest font-semibold">Lecture URLs (up to 3)</p>
                {provostUrls.map((u, i) => (
                  <input
                    key={i}
                    type="text"
                    value={u}
                    onChange={(e) => {
                      const next = [...provostUrls];
                      next[i] = e.target.value;
                      setProvostUrls(next);
                      if (error) setError("");
                    }}
                    placeholder={`YouTube URL ${i + 1}${i === 0 ? " (required)" : " (optional)"}`}
                    className="w-full rounded-xl bg-[#1a1a1a] border border-zinc-800 text-white placeholder-zinc-600 px-5 py-3 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                  />
                ))}
                <p className="text-zinc-500 text-xs uppercase tracking-widest font-semibold mt-1">Learning Objectives</p>
                <textarea
                  value={objectives}
                  onChange={(e) => { setObjectives(e.target.value); if (error) setError(""); }}
                  placeholder={"List your course learning objectives, one per line or as a paragraph..."}
                  rows={4}
                  className="w-full rounded-xl bg-[#1a1a1a] border border-zinc-800 text-white placeholder-zinc-600 px-5 py-3 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
                />
              </div>
            )}

            {error && (
              <p className="text-red-400 text-sm px-1">{error}</p>
            )}

            <button
              type="submit"
              className="w-full py-4 rounded-xl bg-indigo-600 text-white font-semibold text-base hover:bg-indigo-500 hover:scale-105 active:scale-100 transition-all"
            >
              {mode === "provost" ? "Map Curriculum" : "Analyze Lecture"}
            </button>
          </form>

          <div className="w-full grid grid-cols-2 gap-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="flex flex-col gap-1.5 p-3 rounded-xl bg-[#1a1a1a]/70 border border-zinc-800/60 backdrop-blur-sm"
              >
                <span className="text-xl">{f.icon}</span>
                <p className="text-white text-sm font-semibold">{f.title}</p>
                <p className="text-zinc-500 text-xs leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          {/* How it works */}
          <div className="w-full space-y-4">
            <p className="text-center text-zinc-600 text-xs uppercase tracking-widest font-semibold">
              How it works
            </p>
            <div className="flex items-start gap-2">
              <div className="flex-1 flex flex-col items-center gap-2 text-center">
                <div className="w-9 h-9 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center">
                  <span className="text-indigo-400 text-sm font-bold">1</span>
                </div>
                <p className="text-white text-sm font-semibold">Paste URL</p>
                <p className="text-zinc-500 text-xs leading-relaxed">Drop any YouTube lecture link</p>
              </div>
              <span className="text-zinc-700 text-lg mt-3.5 shrink-0">→</span>
              <div className="flex-1 flex flex-col items-center gap-2 text-center">
                <div className="w-9 h-9 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
                  <span className="text-purple-400 text-sm font-bold">2</span>
                </div>
                <p className="text-white text-sm font-semibold">AI Analyzes</p>
                <p className="text-zinc-500 text-xs leading-relaxed">5 AI agents analyze content</p>
              </div>
              <span className="text-zinc-700 text-lg mt-3.5 shrink-0">→</span>
              <div className="flex-1 flex flex-col items-center gap-2 text-center">
                <div className="w-9 h-9 rounded-full bg-violet-500/10 border border-violet-500/30 flex items-center justify-center">
                  <span className="text-violet-400 text-sm font-bold">3</span>
                </div>
                <p className="text-white text-sm font-semibold">Study Smarter</p>
                <p className="text-zinc-500 text-xs leading-relaxed">Study, audit, or map curriculum</p>
              </div>
            </div>
          </div>

          <p className="w-full text-right text-gray-500 text-sm py-4">LectureAI | Jahanvi Jeswani</p>
        </div>
      </main>
    </>
  );
}
