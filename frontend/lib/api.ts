import type { ResearchSessionResponse } from "./types";

// Must be NEXT_PUBLIC_-prefixed since it's read in the browser (the SSE
// hook builds an EventSource URL directly against it). Defaults to the
// docker-compose / local-dev API port.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function startResearch(
  query: string,
): Promise<{ session_id: string; status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return parseOrThrow(res);
}

export async function getResearchSession(
  sessionId: string,
): Promise<ResearchSessionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/research/${sessionId}`, {
    cache: "no-store",
  });
  return parseOrThrow(res);
}

export async function submitPlanReview(
  sessionId: string,
  approved: boolean,
  feedback?: string,
): Promise<{ session_id: string; status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/research/${sessionId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, feedback: feedback ?? null }),
  });
  return parseOrThrow(res);
}

export async function submitReportFeedback(
  reportId: string,
  rating: number,
  comment?: string,
): Promise<{ id: string; rating: number }> {
  const res = await fetch(`${API_BASE_URL}/api/reports/${reportId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, comment: comment ?? null }),
  });
  return parseOrThrow(res);
}

export function streamUrl(sessionId: string): string {
  return `${API_BASE_URL}/api/research/${sessionId}/stream`;
}
