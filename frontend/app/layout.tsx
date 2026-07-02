import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Source_Sans_3 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
});
const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-plex-mono",
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "ORACLE",
  description:
    "An autonomous multi-agent research assistant that reads the web, reasons over it, and writes cited reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${sourceSans.variable} ${plexMono.variable}`}>
      <body className="bg-white text-gray-900">
        {/* ── Premium top nav ──────────────────────────────────────────── */}
        <nav className="sticky top-0 z-50 h-16 m-3 border-b border-gray-100 bg-white/80 backdrop-blur-xl shadow-sm">
          <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-6">
            {/* Brand */}
            <Link href="/" className="group flex items-center gap-3" id="nav-brand">
              {/* Logo mark */}
              <div className="relative flex h-9 w-9 items-center justify-center rounded-xl shadow-md transition-all group-hover:shadow-glow-green">
                <img src="/logo.png" alt="ORACLE Logo" className="h-full w-full object-contain p-1" />
                {/* Sparkle ring */}
                <span className="absolute inset-0 rounded-xl ring-2 ring-emerald-400/0 group-hover:ring-emerald-400/50 transition-all duration-300" />
              </div>
              <div>
                <span className="font-display text-lg font-semibold text-gray-900 tracking-tight">
                  ORACLE
                </span>
                <span className="ml-2 hidden font-mono text-[10px] font-medium tracking-[0.2em] text-gray-400 uppercase sm:inline">
                  Research Intelligence
                </span>
              </div>
            </Link>

            {/* Centre nav */}
            <div className="flex items-center gap-1" role="navigation" aria-label="Main navigation">
              <NavLink href="/" id="nav-home">Home</NavLink>
              <NavLink href="/history" id="nav-history">History</NavLink>
              <NavLink href="/about" id="nav-about">About</NavLink>
            </div>
          </div>
        </nav>

        {children}
      </body>
    </html>
  );
}

function NavLink({ href, id, children }: { href: string; id: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      id={id}
      className="relative rounded-lg px-4 py-2 font-mono text-xs font-semibold tracking-wider text-gray-500 uppercase transition-all hover:text-gray-900 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-emerald-500"
    >
      {children}
    </Link>
  );
}
