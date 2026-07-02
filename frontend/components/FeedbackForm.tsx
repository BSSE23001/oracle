"use client";

import { useState } from "react";
import { submitReportFeedback as submitFeedback } from "@/lib/api";

export function FeedbackForm({ reportId }: { reportId: string }) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === null || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback(reportId, rating, comment.trim() || undefined);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit feedback.");
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="animate-line-in flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-6 py-5 shadow-sm">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-xl text-white shadow-sm">
          ✓
        </span>
        <div>
          <p className="font-mono text-xs font-bold tracking-wider text-emerald-700 uppercase">
            Feedback submitted — thank you!
          </p>
          <p className="mt-0.5 text-sm text-emerald-600">Your rating helps us improve ORACLE.</p>
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
    >
      <div className="mb-5 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 text-white shadow-sm">⭐</span>
        <h2 className="font-mono text-xs font-bold tracking-[0.2em] text-gray-700 uppercase">
          Rate this Report
        </h2>
      </div>

      {/* Star rating */}
      <div className="mb-5 flex gap-2" role="radiogroup" aria-label="Report rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setRating(star)}
            className={`flex h-11 w-11 items-center justify-center rounded-xl border-2 text-xl transition-all active:scale-90 ${
              rating !== null && star <= rating
                ? "border-amber-400 bg-amber-50 shadow-sm scale-105"
                : "border-gray-200 bg-white hover:border-amber-300 hover:bg-amber-50"
            }`}
            aria-label={`${star} star${star > 1 ? "s" : ""}`}
          >
            <span className={rating !== null && star <= rating ? "text-amber-400" : "text-gray-300"}>
              ★
            </span>
          </button>
        ))}
      </div>

      {/* Comment */}
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        placeholder="Optional: any comments on the report quality?"
        id="feedback-comment"
        className="w-full resize-none rounded-xl border border-gray-200 bg-gray-50 p-3.5 text-sm text-gray-700 placeholder:text-gray-400 focus:border-emerald-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-emerald-100 transition-all"
      />

      <div className="mt-4 flex items-center gap-3">
        <button
          type="submit"
          disabled={rating === null || submitting}
          id="feedback-submit"
          className="rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-5 py-2.5 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-md transition-all hover:from-emerald-600 hover:to-emerald-700 active:scale-95 disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300 disabled:shadow-none"
        >
          {submitting ? "Submitting…" : "Submit Feedback"}
        </button>
        {rating === null && (
          <p className="font-mono text-[11px] text-gray-400">Select a star rating first</p>
        )}
      </div>
      {error && <p className="mt-2 font-mono text-xs text-crimson-600">✕ {error}</p>}
    </form>
  );
}
