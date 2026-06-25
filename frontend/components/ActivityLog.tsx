"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/useResearchStream";

const EVENT_ICON: Record<string, string> = {
  session_started: "◎",
  plan_review_required: "⊡",
  plan_decision_received: "▶",
  session_completed: "✓",
  session_failed: "✕",
  node_update: "·",
};

const NODE_COLOR: Record<string, string> = {
  supervisor: "text-honey-700",
  human_review: "text-marigold-600",
  web_search_agent: "text-cobalt-600",
  pdf_agent: "text-cobalt-600",
  code_exec_agent: "text-cobalt-600",
  fact_check_subtask_agent: "text-cobalt-600",
  synthesis_agent: "text-fern-700",
  fact_check_pass: "text-fern-700",
  citation_formatter: "text-fern-700",
};

function fmtTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString(undefined, {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function fmtDelta(ts: number, prev: number | null): string {
  if (prev === null) return "";
  const delta = Math.round((ts - prev) / 1000);
  if (delta < 1) return "";
  return `+${delta}s`;
}

interface ActivityLogProps {
  entries: LogEntry[];
  open: boolean;
  onClose: () => void;
}

export function ActivityLog({ entries, open, onClose }: ActivityLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll to bottom when new entries arrive */
  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [entries.length, open]);

  if (!open) return null;

  const runningCount = entries.filter(
    (e) =>
      e.type === "plan_decision_received" &&
      !entries.some(
        (e2) => e2.type === "session_completed" || e2.type === "session_failed",
      ),
  ).length; // just used for the header label

  return (
    <>
      {/* Backdrop (mobile) */}
      <div
        className="fixed inset-0 z-30 bg-carbon-900/20 lg:hidden"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <aside className="fixed right-0 top-0 z-40 flex h-full w-80 flex-col border-l border-cream-200 bg-white shadow-card-md">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cream-200 px-4 py-3">
          <div>
            <h2 className="font-display text-sm font-semibold text-carbon-900">
              Activity log
            </h2>
            <p className="font-mono text-[10px] text-carbon-300">
              {entries.length} event{entries.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-carbon-400 hover:bg-cream-100 hover:text-carbon-700 transition-colors"
            aria-label="Close activity log"
          >
            ✕
          </button>
        </div>

        {/* Parallel execution note */}
        {entries.some((e) => e.type === "plan_decision_received") && (
          <div className="border-b border-cream-200 bg-cobalt-50 px-4 py-2">
            <p className="font-mono text-[11px] text-cobalt-700">
              ● Specialist agents run in parallel threads — events arrive as
              each finishes, not in dispatch order
            </p>
          </div>
        )}

        {/* Log entries */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
          {entries.length === 0 ? (
            <p className="py-6 text-center font-mono text-[11px] text-carbon-300">
              Waiting for events…
            </p>
          ) : (
            entries.map((entry, i) => {
              const prev = i > 0 ? entries[i - 1].ts : null;
              const delta = fmtDelta(entry.ts, prev);
              const nodeColor = entry.node
                ? (NODE_COLOR[entry.node] ?? "text-carbon-500")
                : "text-carbon-300";
              const isParallelAgent =
                entry.node &&
                [
                  "web_search_agent",
                  "pdf_agent",
                  "code_exec_agent",
                  "fact_check_subtask_agent",
                ].includes(entry.node);

              return (
                <div
                  key={entry.sequence}
                  className={`group flex gap-2 rounded px-2 py-1.5 transition-colors hover:bg-cream-50 ${
                    isParallelAgent ? "border-l-2 border-cobalt-100 pl-2" : ""
                  }`}
                >
                  {/* Icon */}
                  <span
                    className={`mt-0.5 shrink-0 font-mono text-[12px] ${nodeColor}`}
                  >
                    {EVENT_ICON[entry.type] ?? "·"}
                  </span>

                  {/* Body */}
                  <div className="min-w-0 flex-1">
                    <p className="font-body text-[12px] text-carbon-700 leading-snug">
                      {entry.summary}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="font-mono text-[10px] text-carbon-300">
                        {fmtTime(entry.ts)}
                      </span>
                      {delta && (
                        <span className="font-mono text-[10px] text-carbon-300">
                          {delta}
                        </span>
                      )}
                      {entry.node && (
                        <span className={`font-mono text-[10px] ${nodeColor}`}>
                          {entry.node.replace(/_agent$|_/g, (m) =>
                            m === "_agent" ? "" : " ",
                          )}
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
        <div className="border-t border-cream-200 bg-cream-50 px-4 py-2">
          <div className="flex gap-4 font-mono text-[10px] text-carbon-300">
            <span>
              <span className="text-cobalt-600">|</span> parallel agents
            </span>
            <span>
              <span className="text-honey-700">◎</span> plan/review
            </span>
            <span>
              <span className="text-fern-700">✓</span> synthesis
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
