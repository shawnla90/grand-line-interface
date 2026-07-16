"use client";

/**
 * components/Atlas.tsx — the instrument.
 *
 * ONE PIECE OF STATE: `chapter`. Everything on screen — the map's fog, the crew
 * roster, the arc, the saga, the episode number, the voyage strip, the stats — is
 * a pure derivation of it via worldAtChapter(). Nothing else is stored, because
 * anything else stored is something else that can disagree.
 *
 * THE SWEEP. `chapter` is the target; `swept` eases toward it. Small changes
 * (dragging the slider) snap, so dragging stays 1:1. Big changes (typing 1044,
 * clicking a preset, landing on a shared link) tween over about a second, and
 * because the map re-evaluates its fog against the fractional value every frame,
 * the islands do not blink on — they chart themselves one at a time, west to
 * east, in voyage order. That is the whole demo.
 *
 * THE URL IS THE SHARE MECHANIC. ?ch=1044 is written with history.replaceState,
 * not the Next router: the router would round-trip the server on every slider
 * tick and the instrument would feel like a form. The server still reads the
 * param on a cold load, so a shared link renders correctly on first paint.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  worldAtChapter,
  chapterForEpisode,
  episodeForChapter,
  clampChapter,
  type World,
  type Axis,
} from "@/lib/canon";
import { BRAND } from "@/config/brand";
import WorldMap, { type Projection } from "./WorldMap";
import ChapterDock from "./ChapterDock";
import HeroPrompt from "./HeroPrompt";
import Readout from "./Readout";
import CrewRoster from "./CrewRoster";
import IslandDetail from "./IslandDetail";
import Legend from "./Legend";
import Attribution from "./Attribution";

/* -------------------------------------------------------------------------- */
/* the sweep                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Ease `target` into a rendered value. Returns a float — the map wants the
 * fraction so the reveal is continuous rather than stepped.
 */
function useSweep(target: number) {
  const [value, setValue] = useState(target);
  const ref = useRef(target);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (raf.current !== null) cancelAnimationFrame(raf.current);

    const from = ref.current;
    const delta = target - from;
    const dist = Math.abs(delta);

    // Dragging the slider: stay 1:1 or it feels like lag, not polish.
    if (dist <= 4) {
      ref.current = target;
      setValue(target);
      return;
    }

    const duration = Math.min(1500, 260 + dist * 1.15);
    const t0 = performance.now();

    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      const v = from + delta * eased;
      ref.current = v;
      setValue(v);
      raf.current = p < 1 ? requestAnimationFrame(step) : null;
    };

    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [target]);

  return value;
}

/* -------------------------------------------------------------------------- */

type Props = {
  world: World;
  /** null = a cold visit with no ?ch= — show the hero. */
  initialChapter: number | null;
  initialAxis: Axis;
};

const DEFAULT_CHAPTER = 1044;

export default function Atlas({ world, initialChapter, initialAxis }: Props) {
  const [chapter, setChapterRaw] = useState(initialChapter ?? DEFAULT_CHAPTER);
  const [axis, setAxis] = useState<Axis>(initialAxis);
  const [hero, setHero] = useState(initialChapter === null);
  const [projection, setProjection] = useState<Projection>("globe");
  const [offCanon, setOffCanon] = useState(false);
  // Crews & Warlords on the map (Phase 5). Default ON — the chapter gate keeps
  // early chapters clean, so at ch. 1 the layer shows exactly nothing.
  const [showCrews, setShowCrews] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // The episode axis carries its own thumb position — see the note in
  // ChapterDock: episode -> chapter is many-to-one and would otherwise snap.
  const [episode, setEpisodeRaw] = useState(
    () => episodeForChapter(world, initialChapter ?? DEFAULT_CHAPTER) ?? world.episodeMax,
  );

  const swept = useSweep(chapter);
  const shown = clampChapter(world, Math.round(swept));
  const at = useMemo(() => worldAtChapter(world, shown), [world, shown]);

  const setChapter = useCallback(
    (ch: number) => {
      const c = clampChapter(world, ch);
      setChapterRaw(c);
      setEpisodeRaw(episodeForChapter(world, c) ?? world.episodeMax);
    },
    [world],
  );

  const setEpisode = useCallback(
    (ep: number) => {
      setEpisodeRaw(ep);
      setChapterRaw(chapterForEpisode(world, ep));
    },
    [world],
  );

  /* ------------------------------------------------------------------ url */
  useEffect(() => {
    if (hero) return;
    const t = setTimeout(() => {
      const q = new URLSearchParams();
      q.set("ch", String(chapter));
      if (axis === "episode") q.set("axis", "episode");
      window.history.replaceState(null, "", `?${q.toString()}`);
    }, 180);
    return () => clearTimeout(t);
  }, [chapter, axis, hero]);

  /* -------------------------------------------------------------- keyboard */
  useEffect(() => {
    if (hero) return;
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowLeft") setChapter(chapter - (e.shiftKey ? 25 : 1));
      else if (e.key === "ArrowRight") setChapter(chapter + (e.shiftKey ? 25 : 1));
      else if (e.key === "Escape") setSelected(null);
      else if (e.key.toLowerCase() === "g") setProjection((p) => (p === "globe" ? "mercator" : "globe"));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chapter, hero, setChapter]);

  const island = selected ? (world.islands.find((i) => i.slug === selected) ?? null) : null;

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked — the URL is in the address bar anyway */
    }
  };

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-abyss">
      <div className="relative min-h-0 flex-1">
        <WorldMap
          world={world}
          chapter={swept}
          projection={projection}
          showOffCanon={offCanon}
          showCrews={showCrews}
          selected={selected}
          onSelect={setSelected}
        />

        {/* masthead */}
        <div className="pointer-events-none absolute top-0 left-0 z-10 p-5">
          <div className="pointer-events-auto">
            <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-gold/85">
              {BRAND.name}
            </div>
            <p className="mt-1 max-w-[230px] text-[10px] leading-snug text-muted-2">{BRAND.tagline}</p>
          </div>
        </div>

        {/* left rail */}
        {!hero && (
          <aside className="gutter dr-fade absolute top-[74px] bottom-4 left-4 z-10 w-[290px] overflow-y-auto rounded-md border border-rope/70 bg-ink/88 shadow-2xl backdrop-blur">
            <Readout at={at} world={world} />
            {island && <IslandDetail island={island} world={world} onClose={() => setSelected(null)} />}
            <CrewRoster at={at} world={world} />

            <div className="px-5 py-4">
              <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
                What this cannot tell you
              </div>
              <ul className="mt-2 space-y-1.5 text-[10px] leading-snug text-muted-2">
                <li>
                  <span className="text-muted">Bounties are omitted.</span>{" "}
                  The dataset holds one
                  current value per character — printing Luffy&apos;s at chapter 100 would spoil 950
                  chapters.
                </li>
                <li>
                  <span className="text-muted">The anime lags the manga.</span> Chapters{" "}
                  {world.lastAnimatedChapter + 1}–{world.chapterMax} have no episode yet.
                </li>
                <li>
                  <span className="text-muted">The fog is a rendering choice, not encryption.</span>{" "}
                  The dataset ships to your browser; the atlas simply refuses to read ahead for you.
                </li>
              </ul>
            </div>
          </aside>
        )}

        {/* controls + legend */}
        {!hero && (
          <div className="dr-fade absolute top-[74px] right-4 z-10 flex flex-col items-end gap-3">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={share}
                className="rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2 backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
              >
                {copied ? "copied" : "share ch." + at.chapter}
              </button>
              <button
                type="button"
                onClick={() => setProjection((p) => (p === "globe" ? "mercator" : "globe"))}
                title="Toggle projection (G)"
                className="rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2 backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
              >
                {projection === "globe" ? "globe" : "flat"}
              </button>
            </div>

            <button
              type="button"
              onClick={() => setOffCanon((v) => !v)}
              className={[
                "max-w-[254px] rounded-sm border bg-ink/90 px-2.5 py-1.5 text-left font-mono text-[9px] leading-snug tracking-[0.1em] backdrop-blur transition-colors",
                offCanon
                  ? "border-gold/60 text-gold"
                  : "border-rope text-muted-2 hover:border-rope-2 hover:text-muted",
              ].join(" ")}
            >
              {offCanon ? "◉" : "◯"} off-canon: {world.counts.islandsOffCanon} film / anime / game
              locations. No chapter — they cannot be fogged.
            </button>

            <button
              type="button"
              onClick={() => setShowCrews((v) => !v)}
              className={[
                "max-w-[254px] rounded-sm border bg-ink/90 px-2.5 py-1.5 text-left font-mono text-[9px] leading-snug tracking-[0.1em] backdrop-blur transition-colors",
                showCrews
                  ? "border-gold/60 text-gold"
                  : "border-rope text-muted-2 hover:border-rope-2 hover:text-muted",
              ].join(" ")}
            >
              {showCrews ? "◉" : "◯"} who sails here: {world.counts.presenceCrews} crews ·{" "}
              {world.counts.presenceCharacters} Warlords. Chapter-gated, like everything else.
            </button>

            <Legend world={world} at={at} showOffCanon={offCanon} showCrews={showCrews} />
          </div>
        )}

        {hero && (
          <HeroPrompt
            world={world}
            axis={axis}
            onAxis={setAxis}
            onCommit={(n) => {
              if (axis === "chapter") setChapter(n);
              else setEpisode(n);
              setHero(false);
            }}
          />
        )}
      </div>

      {!hero && (
        <ChapterDock
          world={world}
          at={at}
          axis={axis}
          onAxis={setAxis}
          onChapter={setChapter}
          episode={episode}
          onEpisode={setEpisode}
        />
      )}

      <Attribution world={world} />
    </div>
  );
}
