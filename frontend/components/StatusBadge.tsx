import type { SubtaskType } from "@/lib/types";

const LABELS: Record<SubtaskType, string> = {
  web_search: "WEB SEARCH",
  pdf_reader: "PDF READER",
  code_exec: "CODE EXEC",
  fact_check: "FACT CHECK",
};

export function SubtaskTypeTag({ type }: { type: SubtaskType }) {
  return (
    <span className="inline-flex items-center rounded-sm border border-ink-500 bg-ink-700 px-2 py-0.5 font-mono text-[11px] tracking-wider text-brass-300">
      {LABELS[type]}
    </span>
  );
}
