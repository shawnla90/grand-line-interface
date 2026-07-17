"use client";

/**
 * components/Legend.tsx — the confidence key, with live counts.
 *
 * ARCHITECTURE RULE 4, MADE VISIBLE: "Every authored row carries source_ref and
 * canon_confidence. This is rendered in the UI, not just stored."
 *
 * A pin a machine derived from voyage order must not look like a pin a human
 * confirmed against the manga. So confidence is carried by the pin's GEOMETRY,
 * not by a colour a colour-blind reader would miss:
 *
 *   solid disc   canon    — a human checked this
 *   hollow ring  derived  — placed from region + voyage order
 *   ghost dot    guess    — no chapter, no region: an honest placement
 *
 * The counts are live, and right now they read `canon 0`. Every one of the 256
 * mappable islands was positioned by a script. Saying so is the whole difference
 * between a reference work and a repackaging — and it is an open invitation to
 * the fandom to correct it.
 */

import type { World, WorldAt, FruitType, HakiType, StatusKind } from "@/lib/canon";
import { presenceWindowAt, statusHoldersAt } from "@/lib/canon";
import { affiliationColor, crewColor, WARLORD_COLOR } from "@/lib/crews";
import {
  FRUIT_TYPE_ORDER,
  FRUIT_TYPE_STYLE,
  HAKI_RANK,
  HAKI_STYLE,
  STATUS_KINDS,
  STATUS_STYLE,
  UNREVEALED_COLOR,
  focusKey,
  revealedFruit,
  revealedHaki,
  type Focus,
  type PresenceLens,
} from "@/lib/lenses";

/** A legend chip that doubles as the isolate-filter toggle. */
function FocusChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={active ? "Clear filter" : "Show only this on the map"}
      className={[
        "-mx-1 flex items-center gap-1.5 rounded-sm border px-1 py-px text-left transition-colors",
        active ? "border-gold/70 bg-gold/10" : "border-transparent hover:border-rope-2",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function Swatch({ kind }: { kind: "canon" | "derived" | "guess" | "fog" }) {
  const base = "block rounded-full";
  if (kind === "canon")
    return <span className={`${base} h-2.5 w-2.5 bg-gold ring-1 ring-parchment/70`} />;
  if (kind === "derived")
    return <span className={`${base} h-2.5 w-2.5 border-[1.5px] border-gold-2 bg-gold/15`} />;
  if (kind === "guess") return <span className={`${base} h-2 w-2 bg-muted-2/60`} />;
  return <span className={`${base} h-1.5 w-1.5 bg-muted-2/40`} />;
}

function Row({
  kind,
  label,
  note,
  count,
}: {
  kind: "canon" | "derived" | "guess" | "fog";
  label: string;
  note: string;
  count: number | null;
}) {
  return (
    <li className="flex items-start gap-2.5">
      <span className="mt-[3px] flex w-3 justify-center">
        <Swatch kind={kind} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className="text-[11px] text-parchment">{label}</span>
          {count !== null && (
            <span
              className={`tnum font-mono text-[10px] ${
                kind === "canon" && count === 0 ? "text-straw" : "text-muted-2"
              }`}
            >
              {count}
            </span>
          )}
        </span>
        <span className="mt-px block text-[10px] leading-snug text-muted-2">{note}</span>
      </span>
    </li>
  );
}

export default function Legend({
  world,
  at,
  showOffCanon,
  lens,
  focus = null,
  onFocus,
}: {
  world: World;
  at: WorldAt;
  showOffCanon: boolean;
  lens: PresenceLens;
  /** The isolate filter — legend chips toggle it (click again to clear). */
  focus?: Focus | null;
  onFocus?: (f: Focus | null) => void;
}) {
  const pc = world.counts.positionConfidence;
  // focusKey is the identity of a focus everywhere (URL, React keys, this
  // toggle) — comparing kind + a hand-picked field per shape got fragile the
  // moment a shape without `slug` or `type` existed.
  const isActive = (f: Focus) => !!focus && focusKey(focus) === focusKey(f);
  const toggle = (f: Focus) => onFocus?.(isActive(f) ? null : f);

  // Who is on the water at the SHOWN chapter. Names render only for entities the
  // reader has met; the rest collapse into one anonymous count — the same
  // silhouette contract the crew roster keeps.
  const activeCrews = world.presence.crews.filter((c) => presenceWindowAt(c.windows, at.chapter));
  const activeChars = world.presence.characters.filter((c) =>
    presenceWindowAt(c.windows, at.chapter),
  );
  const beyond =
    world.counts.presenceCrews +
    world.counts.presenceCharacters -
    activeCrews.length -
    activeChars.length;

  // The on-board revealed population — the same entities the map's orbs draw
  // this frame. All power bucketing goes through the lib/lenses gates, so the
  // legend can never disagree with the map about what is revealed.
  const onBoard = [
    ...activeCrews.flatMap((c) => c.members.filter((m) => m.fromChapter <= at.chapter)),
    ...activeChars,
  ];
  const fruitCounts = new Map<FruitType, number>();
  const hakiCounts: Record<HakiType, number> = { conqueror: 0, armament: 0, observation: 0 };
  let noFruit = 0;
  let noHaki = 0;
  for (const e of onBoard) {
    const f = revealedFruit(e, at.chapter);
    if (f) fruitCounts.set(f.type, (fruitCounts.get(f.type) ?? 0) + 1);
    else noFruit++;
    const rh = revealedHaki(e, at.chapter);
    if (rh.length === 0) noHaki++;
    for (const h of rh) hakiCounts[h.type]++;
  }

  // ---- the master filter's categories, counted AS OF this chapter.
  // Constructed only where a holder is actually on the board: a chip is built
  // iff its count > 0, so at chapter 1 the strings "Emperors", "Warlords" and
  // "Supernovas" are not in the DOM at all. That is the same constructive gate
  // the search palette keeps — absent, not hidden.
  const onBoardSlugs = new Set<string>();
  for (const c of activeCrews) {
    onBoardSlugs.add(c.slug);
    for (const m of c.members) if (m.fromChapter <= at.chapter) onBoardSlugs.add(m.slug);
  }
  for (const c of activeChars) onBoardSlugs.add(c.slug);
  // the voyage crew is always on the board — it is the ship you are following
  onBoardSlugs.add(world.voyage.crewSlug);
  for (const m of at.crew) onBoardSlugs.add(m.slug);

  const statusCounts = STATUS_KINDS.map((k) => {
    const holders = statusHoldersAt(world, k, at.chapter);
    let n = 0;
    for (const slug of holders) if (onBoardSlugs.has(slug)) n++;
    return { kind: k, count: n };
  }).filter((s) => s.count > 0);

  const affiliationCounts = new Map<string, number>();
  for (const c of activeChars) {
    if (c.affiliation === "Warlord") continue; // the status chip already says this
    affiliationCounts.set(c.affiliation, (affiliationCounts.get(c.affiliation) ?? 0) + 1);
  }

  // Count what is ACTUALLY PLOTTED, not what exists. The off-canon layer is where
  // the `guess` tier lives (no chapter, no region — nothing to derive a position
  // from), so with that layer off the guess count is genuinely zero and the legend
  // says so rather than advertising a pin style that is nowhere on screen.
  let canon = 0;
  let derived = 0;
  let guess = 0;
  const tally = (c: "canon" | "derived" | "guess") => {
    if (c === "canon") canon++;
    else if (c === "derived") derived++;
    else guess++;
  };
  for (const i of at.visibleIslands) tally(i.confidence);
  if (showOffCanon) {
    for (const i of world.islands) {
      if (i.status !== "manga" || i.debutChapter === null) tally(i.confidence);
    }
  }

  return (
    <div className="w-[254px] rounded-md border border-rope/70 bg-ink/90 p-3.5 shadow-2xl backdrop-blur">
      <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
        How much to trust this pin
      </div>

      <ul className="mt-2.5 space-y-2">
        <Row kind="canon" label="Confirmed" note="A human checked the position." count={canon} />
        <Row
          kind="derived"
          label="Derived"
          note="Placed from region + voyage order."
          count={derived}
        />
        <Row kind="guess" label="Guessed" note="No chapter, no region." count={guess} />
        <Row
          kind="fog"
          label="Beyond you"
          note="Charted later in the story."
          count={at.foggedIslands.length}
        />
      </ul>

      {lens !== "off" && (statusCounts.length > 0 || affiliationCounts.size > 0) && (
        <div className="mt-2.5 border-t border-rope/60 pt-2.5">
          <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
            Isolate
          </div>
          <ul className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
            {statusCounts.map(({ kind, count }) => (
              <li key={kind}>
                <FocusChip
                  active={isActive({ kind: "status", status: kind })}
                  onClick={() => toggle({ kind: "status", status: kind })}
                >
                  <span
                    className="block h-2 w-2 rotate-45"
                    style={{ background: STATUS_STYLE[kind].color }}
                  />
                  <span className="text-[10px] text-muted">
                    {STATUS_STYLE[kind].label}{" "}
                    <span className="tnum font-mono text-[9px] text-muted-2">{count}</span>
                  </span>
                </FocusChip>
              </li>
            ))}
            {[...affiliationCounts].map(([name, count]) => (
              <li key={name}>
                <FocusChip
                  active={isActive({ kind: "affiliation", name })}
                  onClick={() => toggle({ kind: "affiliation", name })}
                >
                  <span
                    className="block h-2 w-2 rounded-sm"
                    style={{ background: affiliationColor(name) }}
                  />
                  <span className="text-[10px] text-muted">
                    {name}s{" "}
                    <span className="tnum font-mono text-[9px] text-muted-2">{count}</span>
                  </span>
                </FocusChip>
              </li>
            ))}
          </ul>
        </div>
      )}

      {lens !== "off" && (
        <div className="mt-2.5 border-t border-rope/60 pt-2.5">
          <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
            {lens === "crew" ? "Who sails here" : lens === "fruit" ? "By devil fruit" : "By haki"}
          </div>
          {activeCrews.length + activeChars.length === 0 ? (
            <p className="mt-1.5 text-[10px] leading-snug text-muted-2">
              No one you have met yet.
            </p>
          ) : lens === "crew" ? (
            <ul className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
              {activeCrews.map((c) => (
                <li key={c.slug}>
                  <FocusChip
                    active={focus?.kind === "crew" && focus.slug === c.slug}
                    onClick={() => toggle({ kind: "crew", slug: c.slug })}
                  >
                    <span
                      className="block h-2 w-2 rounded-full"
                      style={{ background: crewColor(c.slug) }}
                    />
                    <span className="text-[10px] text-muted">{c.name}</span>
                  </FocusChip>
                </li>
              ))}
              {activeChars.map((c) => (
                <li key={c.slug}>
                  <FocusChip
                    active={focus?.kind === "crew" && focus.slug === c.slug}
                    onClick={() => toggle({ kind: "crew", slug: c.slug })}
                  >
                    <span
                      className="block h-2 w-2 rounded-full border"
                      style={{ borderColor: WARLORD_COLOR, background: "transparent" }}
                    />
                    <span className="text-[10px] text-muted">{c.name}</span>
                  </FocusChip>
                </li>
              ))}
            </ul>
          ) : lens === "fruit" ? (
            <>
              {/* One chip per type PRESENT among revealed on-board entities —
                  the legend never names a category the map is not showing. */}
              <ul className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
                {fruitCounts.size > 1 && (
                  <li>
                    <FocusChip
                      active={isActive({ kind: "fruit-all" })}
                      onClick={() => toggle({ kind: "fruit-all" })}
                    >
                      <span className="block h-2 w-2 rounded-full border border-gold-2" />
                      <span className="text-[10px] text-muted">
                        all fruits{" "}
                        <span className="tnum font-mono text-[9px] text-muted-2">
                          {onBoard.length - noFruit}
                        </span>
                      </span>
                    </FocusChip>
                  </li>
                )}
                {FRUIT_TYPE_ORDER.filter((t) => (fruitCounts.get(t) ?? 0) > 0).map((t) => (
                  <li key={t}>
                    <FocusChip
                      active={focus?.kind === "fruit" && focus.type === t}
                      onClick={() => toggle({ kind: "fruit", type: t })}
                    >
                      <span
                        className="block h-2 w-2 rounded-full"
                        style={{ background: FRUIT_TYPE_STYLE[t].color }}
                      />
                      <span className="text-[10px] text-muted">
                        {FRUIT_TYPE_STYLE[t].label}{" "}
                        <span className="tnum font-mono text-[9px] text-muted-2">
                          {fruitCounts.get(t)}
                        </span>
                      </span>
                    </FocusChip>
                  </li>
                ))}
                {noFruit > 0 && (
                  <li className="flex items-center gap-1.5">
                    <span
                      className="block h-2 w-2 rounded-full"
                      style={{ background: UNREVEALED_COLOR }}
                    />
                    <span className="text-[10px] text-muted-2">
                      no fruit revealed{" "}
                      <span className="tnum font-mono text-[9px]">{noFruit}</span>
                    </span>
                  </li>
                )}
              </ul>
              <p className="mt-1.5 text-[10px] leading-snug text-muted-2">
                A fruit is a story reveal — it colors in at ITS chapter, not the sailor&apos;s.
              </p>
            </>
          ) : (
            <>
              <ul className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
                {HAKI_RANK.filter((t) => hakiCounts[t] > 0).map((t) => (
                  <li key={t}>
                    <FocusChip
                      active={focus?.kind === "haki" && focus.type === t}
                      onClick={() => toggle({ kind: "haki", type: t })}
                    >
                      <span
                        className="block h-2 w-2 rounded-full"
                        style={{ background: HAKI_STYLE[t].color }}
                      />
                      <span className="text-[10px] text-muted">
                        {HAKI_STYLE[t].label}{" "}
                        <span className="tnum font-mono text-[9px] text-muted-2">
                          {hakiCounts[t]}
                        </span>
                      </span>
                    </FocusChip>
                  </li>
                ))}
                {noHaki > 0 && (
                  <li className="flex items-center gap-1.5">
                    <span
                      className="block h-2 w-2 rounded-full"
                      style={{ background: UNREVEALED_COLOR }}
                    />
                    <span className="text-[10px] text-muted-2">
                      none revealed{" "}
                      <span className="tnum font-mono text-[9px]">{noHaki}</span>
                    </span>
                  </li>
                )}
              </ul>
              <p className="mt-1.5 text-[10px] leading-snug text-muted-2">
                Orb color follows the highest revealed haki: Conqueror over Armament over
                Observation.
              </p>
            </>
          )}
          {focus && (
            <button
              type="button"
              onClick={() => onFocus?.(null)}
              className="mt-1.5 font-mono text-[9px] uppercase tracking-[0.14em] text-gold hover:text-gold-2"
            >
              ✕ clear filter — show everyone
            </button>
          )}
          {beyond > 0 && (
            <p className="mt-1.5 text-[10px] leading-snug text-muted-2">
              {beyond} more beyond your chapter, or off the board.
            </p>
          )}
        </div>
      )}

      {showOffCanon && (
        <p className="mt-2.5 border-t border-rope/60 pt-2.5 text-[10px] leading-snug text-muted-2">
          Gold is in the manga. <span className="text-muted">Grey is not</span> — film, anime-only and
          game locations, shown at the same confidence geometry but off the story&apos;s timeline.
        </p>
      )}

      {pc.canon === 0 && (
        <p className="mt-3 border-t border-rope/60 pt-2.5 text-[10px] leading-snug text-muted-2">
          <span className="text-straw">Not one pin here is human-confirmed.</span> All{" "}
          <span className="tnum">{world.counts.islandsManga}</span>{" "}
          positions were derived by a
          script from each island&apos;s sea and its place in the voyage. Corrections welcome — that
          is the point of showing you.
        </p>
      )}
    </div>
  );
}
