/**
 * components/ui/Panel.tsx — the atlas's panel language, in one place.
 *
 * NO "use client". These are pure presentational components with no state, no
 * effects and no handlers, which means BOTH the server routes (/island/[slug] …)
 * and the existing client rail can import them. A "use client" here would drag
 * every entry page into the client bundle for nothing.
 *
 * These marks were an ad-hoc Tailwind string repeated across IslandDetail,
 * CrewRoster, Readout, Legend and the Atlas rail. That was fine while the rail
 * was the only surface. Four route families are about to need the same look, and
 * the moment to name a pattern is just before you copy it a fifth time.
 *
 * <Receipts> is the one that matters. Rule 4 — every authored row carries a
 * source_ref and it gets RENDERED, verbatim, not summarised — has lived in
 * exactly one component since Phase 5. It is the difference between an atlas and
 * a picture of one, and it is the fastest way for a reader who knows better to
 * tell us we are wrong. It should not be re-typed per route from memory.
 */

import type { ReactNode } from "react";

/** The floating panel: rail, card, page section. */
export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-md border border-rope/70 bg-ink/88 shadow-2xl backdrop-blur ${className}`}
    >
      {children}
    </div>
  );
}

/** A horizontal rule-separated block inside a Panel. */
export function PanelSection({
  children,
  className = "",
  last = false,
}: {
  children: ReactNode;
  className?: string;
  last?: boolean;
}) {
  return (
    <div className={`${last ? "" : "border-b border-rope/60"} px-5 py-4 ${className}`}>
      {children}
    </div>
  );
}

/** The small caps label above every block. The atlas's most repeated mark. */
export function Kicker({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2 ${className}`}
    >
      {children}
    </div>
  );
}

export function FieldGrid({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <dl className={`grid grid-cols-2 gap-x-4 gap-y-2.5 ${className}`}>{children}</dl>;
}

/** A <dt>/<dd> pair. `mono` for coordinates and other figures that must align. */
export function Field({
  label,
  children,
  mono = false,
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">{label}</dt>
      <dd
        className={
          mono
            ? "tnum mt-0.5 font-mono text-[11px] text-muted"
            : "tnum mt-0.5 truncate text-[13px] text-parchment"
        }
      >
        {children}
      </dd>
    </div>
  );
}

export type ConfidenceLevel = "canon" | "derived" | "guess";

/**
 * How much to trust the claim above. Lifted out of IslandDetail — a pin the
 * machine guessed must never look like a pin a human confirmed, and that rule
 * now has to hold on four route families as well as on the map.
 */
const CONFIDENCE_COPY: Record<ConfidenceLevel, { label: string; tone: string }> = {
  canon: { label: "Confirmed by a human", tone: "text-gold" },
  derived: { label: "Position derived", tone: "text-gold-2" },
  guess: { label: "Position guessed", tone: "text-muted" },
};

export function Confidence({
  level,
  label,
  className = "",
}: {
  level: ConfidenceLevel;
  /** Override the copy where "Position" is the wrong noun (a bounty, a reveal). */
  label?: string;
  className?: string;
}) {
  const c = CONFIDENCE_COPY[level];
  return (
    <div className={`font-mono text-[10px] uppercase tracking-[0.16em] ${c.tone} ${className}`}>
      {label ?? c.label}
    </div>
  );
}

/**
 * The receipt, verbatim. Not a summary of it.
 *
 * `sourceRef` is printed exactly as the build artifact carries it — including
 * the ugly ones, because the ugly ones are the honest ones:
 *
 *   "position: derived: region='Paradise'; lng by voyage order 14 (water-7, arc
 *    named after island) | belt model: Grand Line=equator, Red Line=0/180
 *    meridian; deterministic sha256(slug) jitter"
 */
export function Receipts({
  sourceRef,
  wikiUrl,
  linkLabel = "Fandom entry ↗",
  className = "",
}: {
  sourceRef: string;
  wikiUrl?: string | null;
  linkLabel?: string;
  className?: string;
}) {
  return (
    <details className={`group ${className}`}>
      <summary className="cursor-pointer list-none font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2 transition-colors hover:text-muted">
        <span className="group-open:hidden">Show source ▸</span>
        <span className="hidden group-open:inline">Hide source ▾</span>
      </summary>
      <p className="mt-2 border-l border-rope pl-2.5 font-mono text-[10px] leading-relaxed break-words text-muted-2">
        {sourceRef}
      </p>
      {wikiUrl && (
        <a
          href={wikiUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block font-mono text-[10px] text-gold/80 underline underline-offset-2 transition-colors hover:text-gold"
        >
          {linkLabel}
        </a>
      )}
    </details>
  );
}
