"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useResearchStream } from "@/lib/useResearchStream";
import { getResearchSession } from "@/lib/api";
import { PlanReview } from "@/components/PlanReview";
import { AgentWireBoard } from "@/components/AgentWireBoard";
import { ReportView } from "@/components/ReportView";

const PHASE_LABELS: Record<string, string> = {
  connecting: "Connecting to the research desk…",
  planning: "Supervisor is decomposing the query…",
  awaiting_review: "Awaiting your review of the plan",
  dispatching: "Specialists researching in parallel…",
  synthesizing: "Synthesizing findings into a report…",
  fact_checking: "Fact-checking the draft's key claims…",
  formatting_citations: "Resolving citations…",
  completed: "Report complete",
  failed: "Run failed",
};

const WIRE_BOARD_PHASES = ["dispatching", "synthesizing", "fact_checking", "formatting_citations", "completed"];

export default function ResearchSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const state = useResearchStream(sessionId);

  // The SSE-delivered report (from the agent graph's internal schema) has
  // no database id — it's only assigned when the Celery task inserts the
  // `research_reports` row. Fetch it once on completion, purely so the
  // feedback form has something to POST against.
  const [reportId, setReportId] = useState<string | null>(null);
  useEffect(() => {
    if (state.phase !== "completed") return;
    getResearchSession(sessionId)
      .then((session) => setReportId(session.report?.id ?? null))
      .catch(() => setReportId(null));
  }, [state.phase, sessionId]);

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-6 font-mono text-xs">
            <Link href="/history" className="tracking-[0.2em] text-muted-500 uppercase hover:text-brass-300">
              History
            </Link>
            <Link href="/" className="tracking-[0.2em] text-muted-500 uppercase hover:text-brass-300">
              ← ORACLE // RESEARCH DESK
            </Link>
          </div>
          <StatusIndicator phase={state.phase} />
        </header>

        {state.query && <p className="mb-2 font-display text-2xl text-parchment-100 italic">{state.query}</p>}
        <p className="mb-8 font-mono text-xs text-muted-500">{PHASE_LABELS[state.phase] ?? state.phase}</p>

        {state.phase === "failed" && (
          <div className="rounded-md border border-rust-600 bg-ink-700 p-6">
            <p className="font-mono text-xs tracking-wider text-rust-400 uppercase">Run failed</p>
            <p className="mt-2 text-sm text-parchment-300">{state.errorMessage ?? "Unknown error."}</p>
          </div>
        )}

        {state.phase === "awaiting_review" && state.plan && (
          <PlanReview sessionId={sessionId} plan={state.plan} previousFeedback={state.planRevisionFeedback} />
        )}

        {WIRE_BOARD_PHASES.includes(state.phase) && (
          <div className="mb-8">
            <AgentWireBoard phase={state.phase} lanes={state.lanes} />
          </div>
        )}

        {state.phase === "completed" && state.report && (
          <ReportView report={state.report} reportId={reportId} factCheckVerdicts={state.factCheckVerdicts} />
        )}
      </div>
    </main>
  );
}

function StatusIndicator({ phase }: { phase: string }) {
  const done = phase === "completed";
  const failed = phase === "failed";
  return (
    <span
      className={`flex items-center gap-2 font-mono text-xs tracking-wider uppercase ${
        failed ? "text-rust-400" : done ? "text-teal-400" : "text-brass-400"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          failed ? "bg-rust-400" : done ? "bg-teal-400" : "animate-pulse bg-brass-400"
        }`}
      />
      {failed ? "FAILED" : done ? "DONE" : "LIVE"}
    </span>
  );
}
