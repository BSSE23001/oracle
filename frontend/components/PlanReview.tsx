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
    <div className="animate-line-in relative overflow-hidden rounded-3xl border-2 border-amber-300 bg-gradient-to-br from-amber-50 via-white to-yellow-50 p-7 shadow-xl">
      {/* Decorative shimmer sweep */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
        <div className="animate-shimmer absolute inset-0 opacity-40" />
      </div>

      {/* Sparkle */}
      <span aria-hidden className="pointer-events-none absolute right-6 top-4 animate-sparkle text-amber-400 text-2xl">✦</span>

      {/* Header */}
      <div className="relative mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 text-xl shadow-md">
            📋
          </span>
          <div>
            <h2 className="font-mono text-xs font-bold tracking-[0.2em] text-amber-700 uppercase">
              Proposed Research Plan
            </h2>
            <p className="font-mono text-[10px] text-amber-500">{plan.subtasks.length} subtasks planned</p>
          </div>
        </div>
        {previousFeedback && (
          <span className="rounded-full border border-amber-300 bg-white px-3 py-1 font-mono text-[11px] text-amber-700 shadow-sm">
            ↺ revised
          </span>
        )}
      </div>

      {/* Objective */}
      <div className="relative mb-5 rounded-2xl border border-amber-200 bg-white/80 px-5 py-4 shadow-sm backdrop-blur-sm">
        <p className="font-mono text-[10px] font-bold tracking-widest text-amber-500 uppercase mb-1">Objective</p>
        <p className="font-display text-lg text-gray-900 italic leading-snug">{plan.objective}</p>
      </div>

      {/* Subtasks */}
      <ol className="relative space-y-3">
        {plan.subtasks.map((subtask, i) => (
          <li
            key={subtask.id}
            className="flex gap-4 rounded-2xl border border-gray-200 bg-white/90 p-4 shadow-sm backdrop-blur-sm transition-all hover:border-amber-200 hover:shadow-md"
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 font-mono text-xs font-bold text-white shadow-sm">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <SubtaskTypeTag type={subtask.type} />
              <p className="mt-2 text-sm text-gray-600 leading-relaxed">{subtask.description}</p>
              {subtask.input_data && (
                <p className="mt-1.5 font-mono text-[11px] text-gray-400 truncate">
                  → {subtask.input_data}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>

      {/* Actions */}
      <div className="relative mt-6">
        {mode === "idle" ? (
          <div className="flex gap-3">
            <button
              onClick={approve}
              disabled={submitting}
              id="plan-approve-button"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-6 py-3 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-md transition-all hover:from-emerald-600 hover:to-emerald-700 hover:shadow-glow-green active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? (
                <><span className="h-3 w-3 rounded-full border-2 border-white/50 border-t-white animate-spin" />Submitting…</>
              ) : (
                <>✓ Approve & Dispatch</>
              )}
            </button>
            <button
              onClick={() => setMode("feedback")}
              disabled={submitting}
              id="plan-request-changes-button"
              className="rounded-xl border-2 border-gray-200 bg-white px-6 py-3 font-mono text-xs font-bold tracking-wider text-gray-600 uppercase transition-all hover:border-amber-300 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Request Changes
            </button>
          </div>
        ) : (
          <div>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={2}
              placeholder="What should change about the plan?"
              id="plan-feedback-textarea"
              className="w-full rounded-xl border-2 border-gray-200 bg-white p-4 text-sm text-gray-900 placeholder:text-gray-400 focus:border-amber-400 focus:outline-none focus:ring-4 focus:ring-amber-100 transition-all resize-none"
            />
            <div className="mt-3 flex gap-3">
              <button
                onClick={sendFeedback}
                disabled={submitting || !feedback.trim()}
                id="plan-send-feedback-button"
                className="rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 px-5 py-2.5 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-md transition-all hover:shadow-glow-amber active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Sending…" : "Send for Revision"}
              </button>
              <button
                onClick={() => setMode("idle")}
                disabled={submitting}
                id="plan-cancel-button"
                className="rounded-xl border border-gray-200 px-5 py-2.5 font-mono text-xs font-bold tracking-wider text-gray-500 uppercase hover:border-gray-300 hover:text-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        {error && <p className="mt-3 font-mono text-xs text-crimson-600">✕ {error}</p>}
      </div>
    </div>
  );
}
