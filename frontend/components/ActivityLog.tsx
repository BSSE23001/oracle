"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/useResearchStream";

const EVENT_ICON: Record<string, { icon: string; color: string }> = {
  session_started:        { icon: "◎", color: "text-cobalt-500" },
  plan_review_required:   { icon: "⊡", color: "text-amber-500" },
  plan_decision_received: { icon: "▶", color: "text-emerald-500" },
  session_completed:      { icon: "✓", color: "text-emerald-600" },
  session_failed:         { icon: "✕", color: "text-crimson-500" },
  node_update:            { icon: "·", color: "text-gray-400" },
};

const NODE_DOT: Record<string, string> = {
  supervisor:                "bg-amber-400",
  human_review:              "bg-amber-500",
  web_search_agent:          "bg-cobalt-500",
  pdf_agent:                 "bg-amber-500",
  code_exec_agent:           "bg-violet-500",
  fact_check_subtask_agent:  "bg-emerald-500",
  synthesis_agent:           "bg-emerald-600",
  fact_check_pass:           "bg-emerald-600",
  citation_formatter:        "bg-amber-600",
};

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function fmtDelta(ts: number, prev: number | null): string {
  if (prev === null) return "";
  const d = Math.round((ts - prev) / 1000);
  return d >= 1 ? `+${d}s` : "";
}

interface ActivityLogProps {
  entries: LogEntry[];
  open: boolean;
  onClose: () => void;
}

export function ActivityLog({ entries, open, onClose }: ActivityLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [entries.length, open]);

  if (!open) return null;

  const isParallelAgent = (node: string | null) =>
    node ? ["web_search_agent", "pdf_agent", "code_exec_agent", "fact_check_subtask_agent"].includes(node) : false;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-gray-900/20 backdrop-blur-[2px] lg:hidden" onClick={onClose} aria-hidden />

      {/* Panel */}
      <aside className="animate-slide-in-right fixed right-0 top-16 z-40 flex h-[calc(100vh-4rem)] w-84 flex-col border-l border-gray-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-cobalt-500 to-cobalt-700 text-white text-sm shadow-sm">
              📋
            </span>
            <div>
              <h2 className="font-mono text-xs font-bold tracking-wider text-gray-800 uppercase">Activity Log</h2>
              <p className="font-mono text-[10px] text-gray-400">
                {entries.length} event{entries.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
            aria-label="Close activity log"
          >
            ✕
          </button>
        </div>

        {/* Parallel note */}
        {entries.some((e) => e.type === "plan_decision_received") && (
          <div className="shrink-0 border-b border-cobalt-100 bg-cobalt-50 px-5 py-2.5">
            <p className="font-mono text-[10px] text-cobalt-700">
              ⚡ Specialist agents run in parallel — events arrive as each finishes
            </p>
          </div>
        )}

        {/* Entries */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
          {entries.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <div className="mb-3 h-8 w-8 animate-spin-slow rounded-full border-2 border-gray-200 border-t-cobalt-400" />
              <p className="font-mono text-[11px] text-gray-400">Waiting for events…</p>
            </div>
          ) : (
            entries.map((entry, i) => {
              const prev    = i > 0 ? entries[i - 1].ts : null;
              const delta   = fmtDelta(entry.ts, prev);
              const ev      = EVENT_ICON[entry.type] ?? { icon: "·", color: "text-gray-400" };
              const dotBg   = entry.node ? (NODE_DOT[entry.node] ?? "bg-gray-300") : "bg-gray-200";
              const isParal = isParallelAgent(entry.node);
              return (
                <div
                  key={entry.sequence}
                  className={`group flex gap-2 rounded-xl px-3 py-2 transition-colors hover:bg-gray-50 ${isParal ? "border-l-2 border-cobalt-200 ml-1" : ""}`}
                >
                  <span className={`mt-0.5 shrink-0 font-mono text-[13px] ${ev.color}`}>{ev.icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] text-gray-700 leading-snug">{entry.summary}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[10px] text-gray-400">{fmtTime(entry.ts)}</span>
                      {delta && <span className="font-mono text-[10px] text-gray-300">{delta}</span>}
                      {entry.node && (
                        <span className="flex items-center gap-1 font-mono text-[10px] text-gray-500">
                          <span className={`h-1.5 w-1.5 rounded-full ${dotBg}`} />
                          {entry.node.replace(/_agent$/, "").replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>

        {/* Footer legend */}
        <div className="shrink-0 border-t border-gray-100 bg-gray-50 px-5 py-3">
          <div className="flex flex-wrap gap-3 font-mono text-[10px] text-gray-400">
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-cobalt-500" /> parallel</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> planning</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> synthesis</span>
          </div>
        </div>
      </aside>
    </>
  );
}
