export function ConfidenceGauge({ score, size = 96 }: { score: number; size?: number }) {
  const pct = Math.max(0, Math.min(1, score));
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);

  const tone =
    pct >= 0.7
      ? { color: "var(--color-teal-500)", label: "High confidence" }
      : pct >= 0.4
        ? { color: "var(--color-brass-500)", label: "Moderate confidence" }
        : { color: "var(--color-rust-500)", label: "Low confidence" };

  return (
    <div className="flex items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-ink-600)" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={tone.color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-lg text-parchment-100">
          {Math.round(pct * 100)}
          <span className="text-xs text-muted-500">%</span>
        </div>
      </div>
      <div className="font-mono text-xs tracking-wider uppercase" style={{ color: tone.color }}>
        {tone.label}
      </div>
    </div>
  );
}
