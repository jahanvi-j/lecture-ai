"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Mode = "student" | "faculty";

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<Mode>("student");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) {
      setError("Please enter a YouTube URL.");
      return;
    }
    setError("");
    localStorage.setItem("lectureUrl", url.trim());
    localStorage.setItem("lectureMode", mode);
    router.push(`/study?url=${encodeURIComponent(url.trim())}`);
  }

  return (
    <main className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-xl flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <h1 className="text-5xl font-bold text-white tracking-tight">
            LectureAI
          </h1>
          <p className="text-zinc-400 text-lg">
            Turn any lecture into a complete study environment
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
          <input
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (error) setError("");
            }}
            placeholder="Paste a YouTube URL..."
            className="w-full rounded-xl bg-[#1a1a1a] border border-zinc-800 text-white placeholder-zinc-600 px-5 py-4 text-base focus:outline-none focus:border-zinc-500 transition-colors"
          />

          {error && (
            <p className="text-red-400 text-sm px-1">{error}</p>
          )}

          <div className="flex gap-2">
            {(["student", "faculty"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
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

          <button
            type="submit"
            className="w-full py-4 rounded-xl bg-white text-black font-semibold text-base hover:bg-zinc-200 active:bg-zinc-300 transition-colors"
          >
            Analyze Lecture
          </button>
        </form>
      </div>
    </main>
  );
}
