"use client";

import { useState } from "react";
import { submitPlanReview } from "@/lib/api";
import type { ResearchPlan } from "@/lib/types";
import { SubtaskTypeTag } from "@/components/StatusBadge";

export function PlanReview({
  sessionId,
  plan,
  previousFeedback,
}: {
  sessionId: string;
  plan: ResearchPlan;
  previousFeedback: string | null;
}) {
  const [mode, setMode] = useState<"idle" | "feedback">("idle");
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function approve() {
    setSubmitting(true);
    setError(null);
    try {
      await submitPlanReview(sessionId, true);
      // No local state change needed beyond this — the SSE stream delivers
      // `plan_decision_received` then the specialist `node_update` events,
      // and the parent page's reducer moves the whole UI to the next phase.
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit approval.");
      setSubmitting(false);
    }
  }

  async function sendFeedback() {
    if (!feedback.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitPlanReview(sessionId, false, feedback.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit feedback.");
      setSubmitting(false);
    }
  }

  return (
    <div className="animate-line-in rounded-md border border-ink-500 bg-ink-700 p-6 shadow-panel">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">Proposed research plan</h2>
        {previousFeedback && <span className="font-mono text-[11px] text-muted-500">revised per your feedback</span>}
      </div>

      <p className="mb-5 font-display text-lg text-parchment-100 italic">{plan.objective}</p>

      <ol className="space-y-3">
        {plan.subtasks.map((subtask, i) => (
          <li key={subtask.id} className="flex gap-3 rounded-sm border border-ink-600 bg-ink-800 p-3">
            <span className="font-mono text-xs text-muted-600">{String(i + 1).padStart(2, "0")}</span>
            <div className="flex-1">
              <SubtaskTypeTag type={subtask.type} />
              <p className="mt-1.5 text-sm text-parchment-300">{subtask.description}</p>
            </div>
          </li>
        ))}
      </ol>

      {mode === "idle" ? (
        <div className="mt-6 flex gap-3">
          <button
            onClick={approve}
            disabled={submitting}
            className="rounded-sm bg-brass-500 px-4 py-2 font-mono text-xs tracking-wider text-ink-900 uppercase transition-colors hover:bg-brass-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Approve & dispatch"}
          </button>
          <button
            onClick={() => setMode("feedback")}
            disabled={submitting}
            className="rounded-sm border border-ink-500 px-4 py-2 font-mono text-xs tracking-wider text-muted-500 uppercase transition-colors hover:border-brass-500 hover:text-brass-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Request changes
          </button>
        </div>
      ) : (
        <div className="mt-6">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={2}
            placeholder="What should change about the plan?"
            className="w-full rounded-sm border border-ink-500 bg-ink-800 p-3 text-sm text-parchment-100 placeholder:text-muted-600 focus:border-brass-500 focus:outline-none"
          />
          <div className="mt-3 flex gap-3">
            <button
              onClick={sendFeedback}
              disabled={submitting || !feedback.trim()}
              className="rounded-sm bg-brass-500 px-4 py-2 font-mono text-xs tracking-wider text-ink-900 uppercase transition-colors hover:bg-brass-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Submitting…" : "Send for revision"}
            </button>
            <button
              onClick={() => setMode("idle")}
              disabled={submitting}
              className="rounded-sm border border-ink-500 px-4 py-2 font-mono text-xs tracking-wider text-muted-500 uppercase"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-3 font-mono text-xs text-rust-400">{error}</p>}
    </div>
  );
}
