# LectureAI

**Turn any lecture into a complete study environment. Student • Faculty • Provost**

Paste a YouTube lecture URL and LectureAI produces a full set of study materials in under a minute — structured outline, multi-depth summaries, flashcards, semantic search, and a bilingual interface. Professors get a private pedagogical audit that pinpoints exactly what to improve before publishing. Provosts and curriculum designers can map multiple lectures against course objectives to see exactly what is and isn't covered.

---

## What it does

LectureAI processes any YouTube lecture through a five-agent pipeline and returns a rich, interactive study environment. Students get timestamped navigation, adaptive summaries, flip-card flashcards, and semantic search — all in their native language. Faculty get a private improvement report that scores clarity, accessibility, and pedagogical effectiveness, and surfaces the single most impactful change they can make before the next delivery.

---

## Capabilities

### Student Mode

- **Structured outline** — every segment titled and summarized, each with a clickable timestamp that seeks the video
- **Multi-depth summaries** — 90-second brief, 5-minute overview, or full comprehensive notes
- **Flashcards** — 15–25 exam-style cards with source timestamps and difficulty ratings; flip to reveal answers
- **Semantic search** — natural-language search over the full transcript, powered by dense embeddings
- **Bilingual support** — one-click translation to Spanish, French, Hindi, Chinese, or Arabic; original content restored instantly when switching back to English

### Faculty Mode

- **Clarity and pacing audit** — timestamped issues where explanations are confusing, too fast, or assume undisclosed prior knowledge
- **Accessibility and equity analysis** — flags unexplained jargon, culturally exclusive examples, and missing verbal descriptions
- **Pedagogical effectiveness scoring** — logical flow score, student engagement score, and detection of stated learning objectives
- **Priority fix** — one specific improvement with a reason, a timestamp, and a suggested rewrite; the single thing to change before publishing

### Capability 3 — Provost Mode

- Paste up to three YouTube lecture URLs from the same course
- Add course learning objectives (free-form text)
- Get a curriculum coverage map showing which objectives each lecture addresses
- Color-coded status per objective: fully covered / partially covered / missing
- Evidence excerpts with video references and timestamps for each mapped objective

---

## Architecture

Five-agent multi-agent system with real-time streaming progress:

| Agent | Role |
|---|---|
| **Transcript Agent** | Fetches and segments YouTube transcripts via `youtube-transcript-api`; falls back to YouTube Data API v3 on IP blocks with retry logic |
| **Content Intelligence Agent** | Produces a timestamped outline, three-depth summaries, and 5–10 key concepts |
| **Study Materials Agent** | Generates flashcards and builds a dense embedding index for semantic search |
| **Faculty Audit Agent** | Runs four LLM passes — clarity audit, accessibility audit, pedagogical assessment, and priority fix synthesis |
| **Provost Agent** | Parses course learning objectives into structured form, then maps each objective to coverage status (full / partial / missing) across all provided lecture transcripts |
| **Orchestrator** | Coordinates all agents, routes Student / Faculty / Provost modes, and streams live progress events to the frontend via Server-Sent Events |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/stream?url=&mode=` | Student / Faculty streaming analysis via SSE |
| `POST` | `/api/curriculum/stream` | Provost curriculum mapping via SSE |
| `POST` | `/api/search` | Semantic search over a lecture's embedding index |
| `POST` | `/api/translate` | Translate outline, summaries, and flashcards to a target language |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python |
| LLM | Google Gemini 1.5 Flash |
| Embeddings | Gemini `text-embedding-004` |
| Transcript | `youtube-transcript-api` + YouTube Data API v3 fallback |
| Frontend deployment | Vercel |
| Backend deployment | Railway |

---

## Live Demo

| | URL |
|---|---|
| App | https://lecture-ai-six.vercel.app |
| Backend | https://lecture-ai-production-dc0c.up.railway.app |

---

## Local Development

**Prerequisites:** Python 3.11+, Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_key_here
YOUTUBE_API_KEY=your_key_here   # optional — only needed for IP-block fallback
```

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Built for

**Cloudforce Frontier Internship Challenge — May 2026**
