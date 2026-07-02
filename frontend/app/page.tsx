import Link from "next/link";
import { QueryForm } from "@/components/QueryForm";

/* Floating decorative orbs rendered as absolute-positioned divs */
function FloatingOrb({
  size,
  color,
  top,
  left,
  delay,
  duration,
}: {
  size: string;
  color: string;
  top: string;
  left: string;
  delay: string;
  duration: string;
}) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute rounded-full opacity-30 blur-3xl animate-float-slow"
      style={{ width: size, height: size, background: color, top, left, animationDelay: delay, animationDuration: duration }}
    />
  );
}

/* Sparkle particle */
function Sparkle({ style }: { style: React.CSSProperties }) {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute text-amber-400 animate-sparkle select-none"
      style={style}
    >
      ✦
    </span>
  );
}

const FEATURES = [
  { icon: "🔬", label: "Supervisor Planning", color: "from-violet-500 to-purple-600" },
  { icon: "🌐", label: "Web Search", color: "from-cobalt-500 to-cobalt-700" },
  { icon: "📄", label: "PDF Reader", color: "from-amber-500 to-amber-700" },
  { icon: "💻", label: "Code Execution", color: "from-emerald-500 to-emerald-700" },
  { icon: "✅", label: "Fact Checking", color: "from-crimson-500 to-crimson-700" },
  { icon: "📚", label: "Citation Resolver", color: "from-teal-500 to-teal-700" },
];

export default function HomePage() {
  return (
    <main className="relative flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center overflow-hidden bg-white px-6 pb-20">
      {/* ── Background gradient mesh ─────────────────────────────────────── */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        {/* Large gradient blobs */}
        <FloatingOrb size="600px" color="radial-gradient(circle, #6ee7b7 0%, #10b981 60%, transparent 100%)" top="-100px" left="-150px" delay="0s" duration="9s" />
        <FloatingOrb size="500px" color="radial-gradient(circle, #93c5fd 0%, #3b82f6 60%, transparent 100%)" top="100px" left="65%" delay="2s" duration="11s" />
        <FloatingOrb size="400px" color="radial-gradient(circle, #fcd34d 0%, #f59e0b 60%, transparent 100%)" top="60%" left="10%" delay="4s" duration="13s" />
        <FloatingOrb size="350px" color="radial-gradient(circle, #fb7185 0%, #e11d48 60%, transparent 100%)" top="50%" left="75%" delay="1s" duration="10s" />

        {/* Fine grain texture overlay */}
        <div className="absolute inset-0 opacity-[0.015]"
          style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")", backgroundRepeat: "repeat", backgroundSize: "128px" }} />

        {/* Soft radial center glow */}
        <div className="absolute inset-0"
          style={{ background: "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.5) 50%, transparent 100%)" }} />
      </div>

      {/* ── Sparkle particles ───────────────────────────────────────────── */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <Sparkle style={{ top: "15%", left: "8%",  fontSize: "20px", animationDelay: "0.2s", animationDuration: "2.8s" }} />
        <Sparkle style={{ top: "25%", left: "88%", fontSize: "14px", animationDelay: "0.8s", animationDuration: "3.2s" }} />
        <Sparkle style={{ top: "70%", left: "6%",  fontSize: "18px", animationDelay: "1.4s", animationDuration: "2.5s" }} />
        <Sparkle style={{ top: "65%", left: "90%", fontSize: "22px", animationDelay: "0.5s", animationDuration: "3.6s" }} />
        <Sparkle style={{ top: "40%", left: "3%",  fontSize: "12px", animationDelay: "2.1s", animationDuration: "2.9s" }} />
        <Sparkle style={{ top: "80%", left: "50%", fontSize: "16px", animationDelay: "1.0s", animationDuration: "3.1s" }} />
        <Sparkle style={{ top: "10%", left: "55%", fontSize: "24px", animationDelay: "1.7s", animationDuration: "2.7s" }} />
        <Sparkle style={{ top: "55%", left: "70%", fontSize: "13px", animationDelay: "0.3s", animationDuration: "3.4s" }} />
      </div>

      {/* ── Hero content ─────────────────────────────────────────────────── */}
      <div className="animate-line-in flex max-w-4xl flex-col items-center text-center">
        {/* Eyebrow badge */}
        <div className="mb-6 inline-flex items-center gap-2.5 rounded-full border border-emerald-200 bg-white/80 px-5 py-2 shadow-md backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <span className="font-mono text-xs font-semibold tracking-[0.2em] text-emerald-700 uppercase">
            Multi-agent research intelligence
          </span>
        </div>

        {/* Headline */}
        <h1 className="mb-2 font-display text-5xl leading-[1.1] text-gray-900 italic sm:text-6xl lg:text-7xl">
          Ask a question.
        </h1>
        <h1 className="font-display text-5xl leading-[1.1] italic sm:text-6xl lg:text-7xl">
          <span className="gradient-text-green">Watch it get researched.</span>
        </h1>

        {/* Sub-headline */}
        <p className="mt-6 max-w-2xl text-lg text-gray-500 leading-relaxed">
          A supervisor agent decomposes your query into subtasks, dispatches{" "}
          <strong className="font-semibold text-gray-700">specialist agents in parallel</strong>, synthesizes their
          findings into a structured report, and{" "}
          <strong className="font-semibold text-gray-700">fact-checks every claim</strong> before you see it.
        </p>

        {/* Feature pills */}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {FEATURES.map(({ icon, label, color }) => (
            <span
              key={label}
              className="flex items-center gap-2 rounded-full border border-gray-200 bg-white/90 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm backdrop-blur-sm transition-all hover:scale-105 hover:shadow-md"
            >
              <span className={`flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br ${color} text-xs text-white shadow-sm`}>
                {icon}
              </span>
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* ── Query form ───────────────────────────────────────────────────── */}
      <div className="mt-14 w-full max-w-2xl animate-line-in" style={{ animationDelay: "0.15s" }}>
        <QueryForm />
      </div>

      {/* Footer hint */}
      <p className="mt-8 text-sm text-gray-400 animate-fade-in" style={{ animationDelay: "0.3s" }}>
        New to ORACLE?{" "}
        <Link href="/about" className="font-medium text-emerald-600 underline-offset-4 hover:underline">
          Learn how it works →
        </Link>
      </p>

      {/* ── Floating decorative bottom elements ─────────────────────────── */}
      <div aria-hidden className="pointer-events-none absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-3 opacity-30">
        {["bg-emerald-400", "bg-cobalt-400", "bg-amber-400", "bg-crimson-400"].map((c, i) => (
          <div
            key={c}
            className={`h-1.5 w-1.5 rounded-full ${c} animate-float`}
            style={{ animationDelay: `${i * 0.3}s`, animationDuration: `${4 + i * 0.5}s` }}
          />
        ))}
      </div>
    </main>
  );
}
