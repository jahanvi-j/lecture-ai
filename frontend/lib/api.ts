const BASE = "http://localhost:8000";

export async function processLecture(url: string): Promise<any> {
  const res = await fetch(`${BASE}/api/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`Process failed: ${res.status}`);
  return res.json();
}

export async function searchLecture(
  query: string,
  searchIndex: any[]
): Promise<any> {
  const res = await fetch(`${BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, search_index: searchIndex }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export async function translateContent(
  content: any,
  language: string
): Promise<any> {
  const res = await fetch(`${BASE}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, language }),
  });
  if (!res.ok) throw new Error(`Translate failed: ${res.status}`);
  return res.json();
}

export function streamLecture(url: string): EventSource {
  return new EventSource(
    `${BASE}/api/stream?url=${encodeURIComponent(url)}`
  );
}
