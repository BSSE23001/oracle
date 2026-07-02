import type { SubtaskType } from "@/lib/types";

const TYPE_CONFIG: Record<
  SubtaskType,
  { label: string; icon: string; bg: string; text: string; border: string }
> = {
  web_search: {
    label: "Web Search",
    icon: "🌐",
    bg: "bg-cobalt-50",
    text: "text-cobalt-700",
    border: "border-cobalt-200",
  },
  pdf_reader: {
    label: "PDF Reader",
    icon: "📄",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
  },
  code_exec: {
    label: "Code Exec",
    icon: "💻",
    bg: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-200",
  },
  fact_check: {
    label: "Fact Check",
    icon: "✅",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
  },
};

export function SubtaskTypeTag({ type }: { type: SubtaskType }) {
  const cfg = TYPE_CONFIG[type] ?? {
    label: type,
    icon: "·",
    bg: "bg-gray-50",
    text: "text-gray-600",
    border: "border-gray-200",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}
