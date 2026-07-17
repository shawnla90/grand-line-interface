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
 * It is BOTH the map-side hover read and the hero of /character/[slug] — the
 * same poster at two sizes, because it is the same claim. (Its header used to
 * promise "deliberately NOT a route"; the route arrived, so the promise is
 * replaced with what happened.)
 *
 * The prop is a PosterVM, not a WorldCrewMember. That type exists only because
 * crew_joins is hand-authored, and it carries joinChapter/joinArc/order —
 * crew-join facts that 776 of the 786 characters have no business owning. See
 * lib/entry.ts, where the view-model doubles as the compiler-enforced drop-list.
 */

import type { PosterVM } from "@/lib/entry";
import { bountyAt, formatBerry } from "@/lib/canon";

/** rail = the map's hover popover. hero = the page. Same poster, same rules. */
export type PosterSize = "rail" | "hero";

const SIZE = {
  rail: { card: "w-[188px] p-2.5", art: "h-[92px]", name: "text-[15px]", initial: "text-[28px]",
          bounty: "text-[13px]", kicker: "text-[8px] tracking-[0.28em]" },
  hero: { card: "w-[420px] p-5", art: "h-[260px]", name: "text-[30px]", initial: "text-[72px]",
          bounty: "text-[26px]", kicker: "text-[10px] tracking-[0.4em]" },
} as const;

export default function WantedCard({
  poster,
  chapter,
  portrait,
  size = "rail",
}: {
  poster: PosterVM;
  chapter: number;
  portrait?: string;
  size?: PosterSize;
}) {
  const s = SIZE[size];
  const b = bountyAt(poster.bountyHistory, chapter);
  // An epithet rides with the poster: no bounty, no alias. (posterFromCharacter
  // pre-gates this server-side too — this is the client-side half for the map's
  // live scrubbing, where the full history is deliberately present.)
  const epithet = b ? poster.epithet : null;

  return (
    <div className={`${s.card} rounded-sm border border-gold-dim/70 bg-hull/95 shadow-2xl backdrop-blur`}>
      <div className={`text-center font-mono ${s.kicker} uppercase text-gold-2`}>Wanted</div>

      <div className={`mt-1.5 ${s.art} overflow-hidden rounded-sm border border-rope/70 bg-ink/60`}>
        {portrait ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={portrait} alt={poster.name} className="h-full w-full object-cover" />
        ) : (
          <div className={`flex h-full items-center justify-center font-pirate ${s.initial} text-gold-dim`}>
            {poster.name.slice(0, 1)}
          </div>
        )}
      </div>

      <div className="mt-1.5 text-center">
        <div className={`font-pirate ${s.name} leading-tight text-parchment`}>{poster.name}</div>
        {epithet && (
          <div className={`${size === "hero" ? "text-[12px]" : "text-[9px]"} italic leading-snug text-muted`}>
            {epithet}
          </div>
        )}
      </div>

      <div className="mt-1.5 border-t border-rope/60 pt-1.5 text-center">
        {b ? (
          <>
            <div className={`tnum font-mono ${s.bounty} leading-none text-gold`}>
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
        <span>
          {poster.footnote ? `${poster.footnote.label} ch. ${poster.footnote.chapter}` : ""}
        </span>
        {!poster.verified && <span className="text-straw">unverified</span>}
      </div>
    </div>
  );
}
