import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import type { ResearchSessionResponse } from "@/lib/types";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ORACLE | Research History",
  description: "Browse past ORACLE research sessions and reports.",
};

const STATUS_CONFIG: Record<string, {
  text: string; border: string; bg: string; dot: string; icon: string; label: string;
}> = {
  completed:      { text: "text-emerald-700", border: "border-emerald-200", bg: "bg-emerald-50", dot: "bg-emerald-500", icon: "✓", label: "Completed" },
  failed:         { text: "text-crimson-700",  border: "border-crimson-200",  bg: "bg-crimson-50",  dot: "bg-crimson-500",  icon: "✕", label: "Failed" },
  awaiting_review:{ text: "text-amber-700",   border: "border-amber-200",   bg: "bg-amber-50",   dot: "bg-amber-400",   icon: "⊡", label: "Review" },
  running:        { text: "text-amber-700",   border: "border-amber-200",   bg: "bg-amber-50",   dot: "bg-amber-400",   icon: "●", label: "Running" },
  dispatching:    { text: "text-cobalt-700",  border: "border-cobalt-200",  bg: "bg-cobalt-50",  dot: "bg-cobalt-500",  icon: "⚡", label: "Dispatching" },
  planning:       { text: "text-gray-600",    border: "border-gray-200",    bg: "bg-gray-100",   dot: "bg-gray-400",    icon: "◎", label: "Planning" },
  pending:        { text: "text-gray-500",    border: "border-gray-200",    bg: "bg-gray-100",   dot: "bg-gray-300",    icon: "◎", label: "Pending" },
};

async function getSessions(): Promise<ResearchSessionResponse[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/research?limit=40`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function ConfidenceDot({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-400" : "bg-crimson-500";
  return (
    <span className="flex items-center gap-1.5 font-mono text-[11px] text-gray-400">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {pct}% confidence
    </span>
  );
}

export default async function HistoryPage() {
  const sessions = await getSessions();

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-gray-50">
      {/* Header band */}
      <div className="border-b border-gray-100 bg-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end justify-between">
            <div>
              <p className="mb-1 font-mono text-[10px] font-bold tracking-[0.25em] text-gray-400 uppercase">Your work</p>
              <h1 className="font-display text-3xl font-semibold text-gray-900 italic">Research History</h1>
            </div>
            {sessions.length > 0 && (
              <span className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-2 font-mono text-xs font-semibold text-gray-500">
                {sessions.length} session{sessions.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-6 py-8">
        {sessions.length === 0 ? (
          /* Empty state */
          <div className="rounded-3xl border border-dashed border-gray-300 bg-white px-8 py-16 text-center shadow-sm">
            <div className="mb-4 flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-3xl text-white shadow-lg">
                🔍
              </div>
            </div>
            <h2 className="mb-2 font-display text-xl font-semibold text-gray-900">No research sessions yet</h2>
            <p className="mb-8 text-sm text-gray-500 leading-relaxed">
              Ask ORACLE a question and it will plan, research, and write a fully cited report for you.
            </p>
            <Link
              href="/"
              id="history-start-button"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-6 py-3 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-md transition-all hover:from-emerald-600 hover:to-emerald-700 hover:shadow-glow-green active:scale-95"
            >
              Start Researching →
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {sessions.map((session) => {
              const cfg = STATUS_CONFIG[session.status] ?? STATUS_CONFIG.pending;
              const isLive = ["running", "planning", "dispatching", "awaiting_review"].includes(session.status);
              return (
                <li key={session.id}>
                  <Link
                    href={`/research/${session.id}`}
                    className="group flex items-start justify-between gap-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-all duration-200 hover:border-emerald-200 hover:shadow-md"
                  >
                    {/* Left: query + date */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-gray-900 transition-colors group-hover:text-emerald-700">
                        {session.report?.title ?? session.query}
                      </p>
                      {session.report?.title && (
                        <p className="mt-0.5 truncate font-mono text-xs text-gray-400">{session.query}</p>
                      )}
                      <p className="mt-2 font-mono text-[11px] text-gray-400">{fmt(session.created_at)}</p>
                    </div>

                    {/* Right: status + confidence */}
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <span className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-bold uppercase tracking-wider ${cfg.text} ${cfg.border} ${cfg.bg}`}>
                        <span className={`relative flex h-2 w-2 ${isLive ? "" : ""}`}>
                          {isLive && (
                            <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${cfg.dot} opacity-60`} />
                          )}
                          <span className={`relative inline-flex h-2 w-2 rounded-full ${cfg.dot}`} />
                        </span>
                        {cfg.label}
                      </span>
                      {typeof session.report?.confidence_score === "number" && (
                        <ConfidenceDot score={session.report.confidence_score} />
                      )}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}

        {sessions.length > 0 && (
          <div className="mt-8 text-center">
            <Link href="/" className="font-mono text-xs font-semibold text-emerald-600 uppercase tracking-wider hover:underline underline-offset-4">
              + Start a new research session
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
