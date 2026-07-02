export function ConfidenceGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  // Color: <40 crimson, 40-70 amber, >70 emerald
  const isGood = pct >= 70;
  const isMid  = pct >= 40 && pct < 70;

  const color = isGood ? "#10b981" : isMid ? "#f59e0b" : "#e11d48";
  const trackColor = isGood ? "#d1fae5" : isMid ? "#fde68a" : "#fecdd3";
  const label = isGood ? "High" : isMid ? "Medium" : "Low";
  const labelColor = isGood ? "text-emerald-600" : isMid ? "text-amber-600" : "text-crimson-600";
  const bgColor = isGood ? "bg-emerald-50" : isMid ? "bg-amber-50" : "bg-crimson-50";
  const borderColor = isGood ? "border-emerald-200" : isMid ? "border-amber-200" : "border-crimson-200";

  // SVG arc gauge
  const R   = 36;
  const cx  = 48;
  const cy  = 48;
  const arc = 220; // degrees swept
  const startAngle = -110;
  const endAngle   = startAngle + arc * score;

  function polar(deg: number, r: number) {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(start: number, end: number, r: number) {
    const s = polar(start, r);
    const e = polar(end, r);
    const large = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
  }

  return (
    <div className={`flex flex-col items-center rounded-2xl border ${borderColor} ${bgColor} px-5 py-4 shadow-sm`}>
      <svg width="96" height="64" viewBox="0 0 96 72" fill="none" aria-label={`Confidence: ${pct}%`}>
        {/* Track */}
        <path
          d={describeArc(-110, 110, R)}
          stroke={trackColor}
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
        />
        {/* Fill */}
        {score > 0 && (
          <path
            d={describeArc(startAngle, endAngle, R)}
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            fill="none"
            style={{ filter: `drop-shadow(0 0 4px ${color}88)` }}
          />
        )}
        {/* Score text */}
        <text x={cx} y={cy + 6} textAnchor="middle" fill={color} fontSize="15" fontWeight="700" fontFamily="monospace">
          {pct}%
        </text>
      </svg>
      <p className={`-mt-1 font-mono text-xs font-bold uppercase tracking-wider ${labelColor}`}>
        {label} confidence
      </p>
    </div>
  );
}
