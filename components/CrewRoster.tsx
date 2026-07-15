"use client";

/**
 * components/CrewRoster.tsx — ten slots that fill as you read.
 *
 * ============================================================================
 * THE JINBE RULE
 * ============================================================================
 * Every upstream source has a "Debut" field, and Debut is not Join. Jinbe DEBUTS
 * at episode 430 and JOINS at episode 977 — a gap of 547 episodes. Scrape the
 * wiki's Debut field into a join column and Jinbe stands on the Thousand Sunny
 * for 550 episodes in front of the most pedantic fandom on earth.
 *
 * So these ten rows are hand-typed in canon/crew_joins.json, and every one of
 * them is still `verified: false` — nobody has checked them against the manga.
 * This component renders that fact instead of hiding it. An atlas that admits
 * what it has not checked is a reference work; one that doesn't is a guess with
 * good typography.
 *
 * ============================================================================
 * NO BOUNTIES HERE, ON PURPOSE
 * ============================================================================
 * The dataset stores ONE current-day bounty per character. Luffy's is
 * 3,000,000,000. Printing that beside his name at chapter 100 would spoil roughly
 * 950 chapters — in the one app whose entire promise is that it will not. A
 * bounty is only safe to show if it is versioned by chapter, and it is not. Same
 * for `status: alive | dead`. Both are dropped in lib/canon.ts.
 *
 * FUTURE MEMBERS HAVE NO NAME IN THE DOM. An empty slot is a silhouette, not a
 * redacted name — you cannot read it out of the page source.
 */

import type { WorldAt, World } from "@/lib/canon";
import JollyRoger from "./marks/JollyRoger";

export default function CrewRoster({ at, world }: { at: WorldAt; world: World }) {
  const aboard = at.crew;
  const total = world.counts.crew;
  const unverified = world.counts.crew - world.counts.crewVerified;

  return (
    <div className="border-b border-rope/60 px-5 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <JollyRoger crewSlug={world.voyage.crewSlug} size={16} title={world.crewName} />
          <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
            {world.crewName}
          </div>
        </div>
        <div className="tnum font-mono text-[10px] text-muted">
          {aboard.length}/{total}
        </div>
      </div>

      {/* Ten slots. They fill in join order — which is NOT the order the fandom
          recites: by join chapter, Nami is fifth, not third. */}
      <div className="mt-3 grid grid-cols-10 gap-1">
        {Array.from({ length: total }, (_, idx) => {
          const member = aboard[idx];
          const filled = member !== undefined;
          return (
            <div
              key={idx}
              title={filled ? `${member.name} — joined ch. ${member.joinChapter}` : "Not yet aboard"}
              className={[
                "h-9 rounded-sm border transition-all duration-500",
                filled
                  ? "border-gold/70 bg-gold/15 shadow-[0_0_12px_-2px_rgba(227,176,75,.5)]"
                  : "border-rope/70 bg-hull/40",
              ].join(" ")}
            >
              {filled && (
                <div className="flex h-full items-center justify-center font-mono text-[10px] font-medium text-gold-2">
                  {member.name.slice(0, 1)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <ul className="mt-3 space-y-1">
        {aboard.map((m) => (
          <li key={m.slug} className="dr-enter flex items-baseline justify-between gap-2">
            <span className="truncate text-[12px] text-parchment">{m.name}</span>
            <span className="tnum shrink-0 font-mono text-[10px] text-muted-2">ch. {m.joinChapter}</span>
          </li>
        ))}
        {aboard.length === 0 && (
          <li className="text-[11px] text-muted-2">Nobody aboard yet.</li>
        )}
      </ul>

      {unverified > 0 && (
        <div className="mt-3 flex items-start gap-1.5 rounded-sm border border-straw/30 bg-straw/5 px-2 py-1.5">
          <span className="mt-px font-mono text-[9px] leading-none text-straw">!</span>
          <p className="text-[10px] leading-snug text-muted">
            <span className="text-straw">{unverified} of {total} join chapters unverified.</span>{" "}
            Hand-typed, not scraped — every wiki&apos;s “Debut” field is wrong for all ten. Not yet
            confirmed against the manga.
          </p>
        </div>
      )}
    </div>
  );
}
