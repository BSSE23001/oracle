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
    <div className="w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="relative">
        <label htmlFor="query" className="mb-2 block font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
          Transmit query
        </label>
        <div className="relative rounded-md border border-ink-500 bg-ink-700 shadow-panel transition-colors focus-within:border-brass-500">
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What do you want researched?"
            rows={3}
            disabled={submitting}
            className="w-full resize-none bg-transparent p-4 pr-32 font-body text-base text-parchment-100 placeholder:text-muted-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={submitting || query.trim().length < 3}
            className="absolute bottom-3 right-3 rounded-sm bg-brass-500 px-4 py-2 font-mono text-xs tracking-wider text-ink-900 uppercase transition-colors hover:bg-brass-400 disabled:cursor-not-allowed disabled:bg-ink-500 disabled:text-muted-500"
          >
            {submitting ? "Dispatching…" : "Dispatch ▸"}
          </button>
        </div>
        {error && <p className="mt-2 font-mono text-xs text-rust-400">{error}</p>}
      </form>

      <div className="mt-6 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuery(example)}
            className="rounded-sm border border-ink-600 px-3 py-1.5 font-mono text-xs text-muted-500 transition-colors hover:border-brass-500 hover:text-brass-300"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
