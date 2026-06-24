import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import type { ResearchSessionResponse } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  completed: "text-teal-400 border-teal-600",
  failed: "text-rust-400 border-rust-600",
  awaiting_review: "text-brass-400 border-brass-600",
  running: "text-brass-400 border-brass-600",
  dispatching: "text-brass-400 border-brass-600",
  planning: "text-muted-500 border-ink-500",
  pending: "text-muted-500 border-ink-500",
};

async function getSessions(): Promise<ResearchSessionResponse[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/research?limit=40`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default async function HistoryPage() {
  const sessions = await getSessions();

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="mb-8 flex items-center justify-between">
          <Link
            href="/"
            className="font-mono text-xs tracking-[0.2em] text-muted-500 uppercase hover:text-brass-300"
          >
            ← ORACLE // RESEARCH DESK
          </Link>
        </header>

        <h1 className="mb-8 font-display text-2xl text-parchment-100">Research history</h1>

        {sessions.length === 0 ? (
          <div className="rounded-md border border-ink-600 bg-ink-700 p-8 text-center">
            <p className="font-mono text-xs text-muted-500">No research sessions yet.</p>
            <Link
              href="/"
              className="mt-4 inline-block font-mono text-xs tracking-wider text-brass-400 uppercase hover:text-brass-300"
            >
              Start one →
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {sessions.map((session) => (
              <li key={session.id}>
                <Link
                  href={`/research/${session.id}`}
                  className="flex items-start justify-between gap-4 rounded-md border border-ink-600 bg-ink-700 p-4 transition-colors hover:border-brass-500"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-parchment-100">
                      {session.report?.title ?? session.query}
                    </p>
                    {session.report?.title && (
                      <p className="mt-0.5 truncate font-mono text-xs text-muted-500">{session.query}</p>
                    )}
                    <p className="mt-1 font-mono text-[11px] text-muted-600">{fmt(session.created_at)}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span
                      className={`rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${
                        STATUS_STYLES[session.status] ?? STATUS_STYLES.pending
                      }`}
                    >
                      {session.status}
                    </span>
                    {typeof session.report?.confidence_score === "number" && (
                      <span className="font-mono text-[11px] text-muted-600">
                        {Math.round(session.report.confidence_score * 100)}% confidence
                      </span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
