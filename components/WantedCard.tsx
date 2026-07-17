"use client";

/**
 * components/WantedCard.tsx — a wanted poster, as of your chapter.
 *
 * One Piece's own UI primitive for "here is a person and what the world thinks
 * they are worth". Everything on it is chapter-gated by the same helpers the map
 * uses, so the card cannot know more than the reader:
 *
 *   - the bounty is bountyAt(), so it reads 30,000,000 at ch. 96 and
 *     3,000,000,000 only at 1053;
 *   - the EPITHET is gated on the first bounty, because an epithet is poster
 *     text — nobody calls him "Straw Hat Luffy" at chapter 50, they call him
 *     "some kid in a straw hat". No bounty, no alias;
 *   - before any of that the card says "no bounty posted yet", which is a fact
 *     about the story rather than an absence of data.
 *
 * Deliberately NOT a route. Phase 8 turns these into /character/[slug] pages
 * with OG cards; this is the map-side read, and it ships now because the data
 * finally exists to make it honest.
 */

import type { WorldCrewMember } from "@/lib/canon";
import { bountyAt, formatBerry } from "@/lib/canon";

export default function WantedCard({
  member,
  chapter,
  portrait,
}: {
  member: WorldCrewMember;
  chapter: number;
  portrait?: string;
}) {
  const b = bountyAt(member.bountyHistory, chapter);
  // An epithet rides with the poster: no bounty, no alias.
  const epithet = b ? member.epithet : null;

  return (
    <div className="w-[188px] rounded-sm border border-gold-dim/70 bg-hull/95 p-2.5 shadow-2xl backdrop-blur">
      <div className="text-center font-mono text-[8px] uppercase tracking-[0.28em] text-gold-2">
        Wanted
      </div>

      <div className="mt-1.5 h-[92px] overflow-hidden rounded-sm border border-rope/70 bg-ink/60">
        {portrait ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={portrait} alt={member.name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center font-pirate text-[28px] text-gold-dim">
            {member.name.slice(0, 1)}
          </div>
        )}
      </div>

      <div className="mt-1.5 text-center">
        <div className="font-pirate text-[15px] leading-tight text-parchment">{member.name}</div>
        {epithet && <div className="text-[9px] italic leading-snug text-muted">{epithet}</div>}
      </div>

      <div className="mt-1.5 border-t border-rope/60 pt-1.5 text-center">
        {b ? (
          <>
            <div className="tnum font-mono text-[13px] leading-none text-gold">
              {formatBerry(b.amount)}
            </div>
            <div className="mt-1 font-mono text-[8px] uppercase tracking-[0.14em] text-muted-2">
              as of ch. {b.asOfChapter}
            </div>
          </>
        ) : (
          <div className="text-[10px] italic text-muted-2">no bounty posted yet</div>
        )}
      </div>

      <div className="mt-1.5 flex items-center justify-between border-t border-rope/60 pt-1.5 font-mono text-[8px] uppercase tracking-[0.12em] text-muted-2">
        <span>joined ch. {member.joinChapter}</span>
        {!member.verified && <span className="text-straw">unverified</span>}
      </div>
    </div>
  );
}
