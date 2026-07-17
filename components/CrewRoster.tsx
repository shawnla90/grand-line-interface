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
 * BOUNTIES, VERSIONED BY CHAPTER
 * ============================================================================
 * This panel used to refuse bounties outright, and the reason was sound: the
 * dataset stored ONE current-day value per character. Luffy's is 3,000,000,000,
 * and printing that beside his name at chapter 100 spoils ~950 chapters in the
 * one app whose whole promise is that it won't.
 *
 * The rule was never "no bounties" — it was "no bounty we cannot fog". Phase 7B
 * parsed the wiki's full progression WITH the chapter each amount was revealed
 * in, so now there is one we can: bountyAt(history, ch) resolves what the reader
 * has actually been shown, and the number ticks up as they read — 30M at 96,
 * 100M at 213, 300M at 435. `status: alive | dead` is still a single
 * present-day value and is still dropped.
 *
 * null from bountyAt is not missing data, it is the story: Luffy has no bounty
 * until Arlong Park, so the row says so rather than showing a blank.
 *
 * FUTURE MEMBERS HAVE NO NAME IN THE DOM. An empty slot is a silhouette, not a
 * redacted name — you cannot read it out of the page source. Same for the
 * numbers: an unrevealed bounty is not in the page at all.
 */

import { useState } from "react";
import type { WorldAt, World, WorldCrewMember } from "@/lib/canon";
import { bountyAt, formatBerry } from "@/lib/canon";
import type { Art } from "@/lib/art";
import JollyRoger from "./marks/JollyRoger";
import WantedCard from "./WantedCard";

export default function CrewRoster({ at, world, art }: { at: WorldAt; world: World; art: Art }) {
  const aboard = at.crew;
  const total = world.counts.crew;
  const unverified = world.counts.crew - world.counts.crewVerified;
  // The hovered slot's poster. Only ever set from an ABOARD member, so an empty
  // slot cannot open a card for someone the reader has not met.
  const [poster, setPoster] = useState<WorldCrewMember | null>(null);

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
      <div className="relative mt-3 grid grid-cols-10 gap-1">
        {Array.from({ length: total }, (_, idx) => {
          const member = aboard[idx];
          const filled = member !== undefined;
          // Only aboard members carry a portrait. An empty slot has no name and no
          // image src in the DOM — a silhouette, not a redacted spoiler.
          const portrait = filled ? art.characters[member.slug] : undefined;
          return (
            <div
              key={idx}
              title={filled ? `${member.name} — joined ch. ${member.joinChapter}` : "Not yet aboard"}
              onMouseEnter={() => filled && setPoster(member)}
              onMouseLeave={() => filled && setPoster(null)}
              className={[
                "h-9 overflow-hidden rounded-sm border transition-all duration-500",
                filled
                  ? "border-gold/70 bg-gold/15 shadow-[0_0_12px_-2px_rgba(227,176,75,.5)]"
                  : "border-rope/70 bg-hull/40",
              ].join(" ")}
            >
              {filled &&
                (portrait ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={portrait} alt={member.name} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full items-center justify-center font-mono text-[10px] font-medium text-gold-2">
                    {member.name.slice(0, 1)}
                  </div>
                ))}
            </div>
          );
        })}
        {poster && (
          <div className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 -translate-x-1/2">
            <WantedCard
              member={poster}
              chapter={at.chapter}
              portrait={art.characters[poster.slug]}
            />
          </div>
        )}
      </div>

      <ul className="mt-3 space-y-1.5">
        {aboard.map((m) => {
          const b = bountyAt(m.bountyHistory, at.chapter);
          return (
            <li key={m.slug} className="dr-enter flex items-baseline justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5">
                {art.characters[m.slug] && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={art.characters[m.slug]}
                    alt=""
                    className="h-4 w-4 shrink-0 rounded-full object-cover ring-1 ring-gold/40"
                  />
                )}
                <span className="min-w-0">
                  <span className="block truncate text-[12px] text-parchment">{m.name}</span>
                  {b ? (
                    <span className="tnum block font-mono text-[10px] text-gold-2">
                      {formatBerry(b.amount)}
                    </span>
                  ) : (
                    <span className="block text-[10px] italic text-muted-2">
                      no bounty posted yet
                    </span>
                  )}
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span className="tnum block font-mono text-[10px] text-muted-2">
                  ch. {m.joinChapter}
                </span>
                {b && (
                  <span className="tnum block font-mono text-[9px] text-muted-2/70">
                    as of {b.asOfChapter}
                  </span>
                )}
              </span>
            </li>
          );
        })}
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
