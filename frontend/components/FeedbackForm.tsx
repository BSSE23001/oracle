"use client";

import { useState } from "react";
import { submitReportFeedback } from "@/lib/api";

export function FeedbackForm({ reportId }: { reportId: string }) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(selected: number) {
    setRating(selected);
    try {
      await submitReportFeedback(reportId, selected, comment.trim() || undefined);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit feedback.");
    }
  }

  if (submitted) {
    return <p className="font-mono text-xs text-teal-400">Feedback recorded — thank you.</p>;
  }

  return (
    <div className="rounded-md border border-ink-600 bg-ink-700 p-5">
      <p className="mb-3 font-mono text-xs tracking-wider text-brass-400 uppercase">Rate this report</p>
      <div className="mb-3 flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => setRating(n)}
            className={`h-9 w-9 rounded-sm border font-mono text-sm transition-colors ${
              rating === n
                ? "border-brass-500 bg-brass-500 text-ink-900"
                : "border-ink-500 text-muted-500 hover:border-brass-500 hover:text-brass-300"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        placeholder="Anything specific about the citations, synthesis, or accuracy? (optional)"
        className="w-full rounded-sm border border-ink-500 bg-ink-800 p-3 text-sm text-parchment-100 placeholder:text-muted-600 focus:border-brass-500 focus:outline-none"
      />
      <button
        onClick={() => rating && submit(rating)}
        disabled={!rating}
        className="mt-3 rounded-sm bg-brass-500 px-4 py-2 font-mono text-xs tracking-wider text-ink-900 uppercase transition-colors hover:bg-brass-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Submit feedback
      </button>
      {error && <p className="mt-2 font-mono text-xs text-rust-400">{error}</p>}
    </div>
  );
}
