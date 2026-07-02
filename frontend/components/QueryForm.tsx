"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch } from "@/lib/api";

const EXAMPLES = [
  "What are the main approaches to retrieval-augmented generation?",
  "How effective are GLP-1 drugs for long-term weight maintenance?",
  "What's driving the recent drop in global shipping container rates?",
];

export function QueryForm() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim().length < 3 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { session_id } = await startResearch(query.trim());
      router.push(`/research/${session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the research run.");
      setSubmitting(false);
    }
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="relative">
        {/* Glow behind the textarea */}
        <div
          aria-hidden
          className="pointer-events-none absolute -inset-1 rounded-2xl opacity-0 transition-opacity duration-500 focus-within:opacity-100"
          style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.15) 0%, transparent 70%)" }}
        />

        <div className="relative overflow-hidden rounded-2xl border-2 border-gray-200 bg-white shadow-lg transition-all duration-300 focus-within:border-emerald-400 focus-within:shadow-glow-green">
          {/* Shimmer sweep on focus */}
          <div className="pointer-events-none absolute inset-0 -z-10 opacity-0 transition-opacity focus-within:opacity-100">
            <div className="animate-shimmer absolute inset-0" />
          </div>

          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What do you want researched? Ask anything…"
            rows={3}
            disabled={submitting}
            className="w-full resize-none bg-transparent p-5 pr-36 font-body text-base text-gray-900 placeholder:text-gray-400 focus:outline-none"
          />

          {/* Character hints */}
          {query.length > 0 && (
            <span className="absolute bottom-4 left-5 font-mono text-[10px] text-gray-300">
              {query.length} chars
            </span>
          )}

          <button
            type="submit"
            id="query-submit"
            disabled={submitting || query.trim().length < 3}
            className="absolute right-4 bottom-4 flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-5 py-2.5 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-md transition-all hover:from-emerald-600 hover:to-emerald-700 hover:shadow-glow-green active:scale-95 disabled:cursor-not-allowed disabled:from-gray-300 disabled:to-gray-300 disabled:shadow-none"
          >
            {submitting ? (
              <>
                <span className="h-3 w-3 rounded-full border-2 border-white/50 border-t-white animate-spin" />
                Dispatching…
              </>
            ) : (
              <>Dispatch ▸</>
            )}
          </button>
        </div>

        {error && (
          <p className="mt-2 flex items-center gap-1.5 font-mono text-xs text-crimson-600">
            <span>✕</span> {error}
          </p>
        )}
      </form>

      {/* Example queries */}
      <div className="mt-5 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuery(example)}
            className="rounded-full border border-gray-200 bg-white/80 px-3.5 py-1.5 font-body text-xs text-gray-500 shadow-sm backdrop-blur-sm transition-all hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 hover:shadow-md active:scale-95"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
