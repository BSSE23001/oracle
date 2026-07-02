"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useResearchStream } from "@/lib/useResearchStream";
import { getResearchSession } from "@/lib/api";
import { PlanReview } from "@/components/PlanReview";
import { AgentWireBoard } from "@/components/AgentWireBoard";
import { ReportView } from "@/components/ReportView";
import { ActivityLog } from "@/components/ActivityLog";

const PHASE_LABELS: Record<string, string> = {
  connecting:           "Connecting to the research engine…",
  planning:             "Supervisor is decomposing your query…",
  awaiting_review:      "Awaiting your review of the research plan",
  dispatching:          "Specialist agents are researching in parallel…",
  synthesizing:         "Synthesizing findings into a structured report…",
  fact_checking:        "Fact-checking the draft's key claims…",
  formatting_citations: "Resolving citations and formatting the report…",
  completed:            "Report complete ✓",
  failed:               "Research run failed",
};

const WIRE_BOARD_PHASES = [
  "dispatching", "synthesizing", "fact_checking", "formatting_citations", "completed",
];

function PhaseBanner({ phase }: { phase: string }) {
  const isActive = !["completed", "failed"].includes(phase);
  return (
    <div className={`flex items-center gap-2.5 rounded-2xl px-5 py-3 font-mono text-sm transition-all ${
      isActive ? "bg-amber-50 border border-amber-200 text-amber-700" : "bg-gray-50 border border-gray-200 text-gray-500"
    }`}>
      {isActive && (
        <span className="relative flex h-2.5 w-2.5 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
        </span>
      )}
      {PHASE_LABELS[phase] ?? phase}
    </div>
  );
}

function StatusPill({ phase }: { phase: string }) {
  const done   = phase === "completed";
  const failed = phase === "failed";
  return (
    <span className={`shrink-0 flex items-center gap-2 rounded-full border px-4 py-1.5 font-mono text-xs font-bold tracking-wider uppercase ${
      failed ? "border-crimson-200 bg-crimson-50 text-crimson-600"
             : done ? "border-emerald-200 bg-emerald-50 text-emerald-700"
             : "border-amber-200 bg-amber-50 text-amber-600"
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${
        failed ? "bg-crimson-500" : done ? "bg-emerald-500" : "bg-amber-500 animate-pulse"
      }`} />
      {failed ? "FAILED" : done ? "DONE" : "LIVE"}
    </span>
  );
}

export default function ResearchSessionPage() {
  const params    = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const state     = useResearchStream(sessionId);
  const [logOpen, setLogOpen]   = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);

  useEffect(() => {
    if (state.phase !== "completed") return;
    getResearchSession(sessionId)
      .then((s) => setReportId(s.report?.id ?? null))
      .catch(() => setReportId(null));
  }, [state.phase, sessionId]);

  const logCount = state.log.length;

  return (
    <main className="relative min-h-[calc(100vh-4rem)] bg-gray-50 px-6 py-10">
      {/* Subtle background gradient */}
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10"
        style={{ background: "radial-gradient(ellipse 70% 40% at 80% 20%, rgba(16,185,129,0.05) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 20% 80%, rgba(59,130,246,0.05) 0%, transparent 70%)" }} />

      <div className="mx-auto max-w-4xl">
        {/* Page header */}
        <header className="mb-7">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              {state.query && (
                <h1 className="font-display text-2xl font-semibold text-gray-900 italic leading-snug sm:text-3xl">
                  {state.query}
                </h1>
              )}
              {!state.query && (
                <div className="h-8 w-64 animate-pulse rounded-xl bg-gray-200" />
              )}
            </div>
            <StatusPill phase={state.phase} />
          </div>
          <div className="mt-3">
            <PhaseBanner phase={state.phase} />
          </div>
        </header>

        {/* Error */}
        {state.phase === "failed" && (
          <div className="mb-8 animate-line-in rounded-2xl border-2 border-crimson-200 bg-crimson-50 p-6 shadow-sm">
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-crimson-500 text-white text-sm shadow-sm">✕</span>
              <p className="font-mono text-xs font-bold tracking-wider text-crimson-700 uppercase">Research Run Failed</p>
            </div>
            <p className="text-sm text-crimson-700">{state.errorMessage ?? "Unknown error."}</p>
          </div>
        )}

        {/* Plan review */}
        {state.phase === "awaiting_review" && state.plan && (
          <div className="mb-8">
            <PlanReview sessionId={sessionId} plan={state.plan} previousFeedback={state.planRevisionFeedback} />
          </div>
        )}

        {/* Wire board */}
        {WIRE_BOARD_PHASES.includes(state.phase) && (
          <div className="mb-8">
            <AgentWireBoard phase={state.phase} lanes={state.lanes} />
          </div>
        )}

        {/* Report */}
        {state.phase === "completed" && state.report && (
          <ReportView report={state.report} reportId={reportId} factCheckVerdicts={state.factCheckVerdicts} />
        )}

        {/* Connecting / planning skeleton */}
        {(state.phase === "connecting" || state.phase === "planning") && (
          <div className="animate-pulse space-y-4 pt-4">
            <div className="h-4 w-3/4 rounded-full bg-gray-200" />
            <div className="h-4 w-1/2 rounded-full bg-gray-200" />
            <div className="h-4 w-2/3 rounded-full bg-gray-200" />
            <div className="mt-6 h-48 rounded-2xl bg-gray-200" />
          </div>
        )}
      </div>

      {/* Activity Log */}
      <ActivityLog entries={state.log} open={logOpen} onClose={() => setLogOpen(false)} />

      {/* Floating toggle button */}
      <button
        onClick={() => setLogOpen((p) => !p)}
        id="activity-log-toggle"
        aria-label={logOpen ? "Close activity log" : "Open activity log"}
        title="Activity Log"
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-2xl shadow-xl transition-all duration-300 active:scale-90 ${
          logOpen
            ? "bg-gray-700 text-white hover:bg-gray-800"
            : "bg-gradient-to-br from-cobalt-500 to-cobalt-700 text-white hover:shadow-glow-blue"
        }`}
      >
        <span className="text-xl leading-none select-none">{logOpen ? "✕" : "📋"}</span>
        {!logOpen && logCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-400 px-1 font-mono text-[10px] font-bold text-white shadow-md">
            {logCount > 99 ? "99+" : logCount}
          </span>
        )}
      </button>
    </main>
  );
}
