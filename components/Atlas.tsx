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
  presenceWindowAt,
  type World,
  type Axis,
} from "@/lib/canon";
import { BRAND } from "@/config/brand";
import type { Focus, PresenceLens } from "@/lib/lenses";
import type { BuildLog } from "@/lib/buildlog";
import type { Art } from "@/lib/art";
import WorldMap, { type Projection } from "./WorldMap";
import SearchPalette, { type SearchHit } from "./SearchPalette";
import ChapterDock from "./ChapterDock";
import HeroPrompt from "./HeroPrompt";
import Readout from "./Readout";
import CrewRoster from "./CrewRoster";
import IslandDetail from "./IslandDetail";
import Legend from "./Legend";
import Attribution from "./Attribution";

/* -------------------------------------------------------------------------- */
/* the chapter engine — sweep tween + story playback, one rAF at a time        */
/* -------------------------------------------------------------------------- */

export const SPEEDS = [0.5, 1, 2, 4] as const;
export type Speed = (typeof SPEEDS)[number];
/** Chapters per second at 1x. 2 ch/s sails the whole story in ~10 minutes. */
const BASE_CPS = 2;

/**
 * One float position (`swept`) eased or sailed toward/through chapters.
 *
 * TWEEN (manual sets): small deltas snap 1:1 (slider drags must not lag),
 * big jumps ease out over ~a second — unchanged from the original sweep.
 *
 * PLAY ("sail the story"): the position advances at speed x BASE_CPS,
 * bypassing the tween entirely, so the reveal is perfectly continuous at any
 * speed. The integer `chapter` stays derived from the float (URL, readout,
 * roster all follow), and playback auto-pauses at the last chapter.
 */
function useChapterEngine(world: World, initial: number) {
  const [chapter, setChapterState] = useState(initial);
  const [swept, setSwept] = useState(initial);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const pos = useRef(initial); // the float truth both loops write
  const raf = useRef<number | null>(null);
  const playingRef = useRef(false);

  // tween toward a manually-set target (skipped while playback owns the float)
  useEffect(() => {
    if (playingRef.current) {
      pos.current = chapter; // playback wrote chapter itself; nothing to ease
      return;
    }
    if (raf.current !== null) cancelAnimationFrame(raf.current);

    const from = pos.current;
    const delta = chapter - from;
    const dist = Math.abs(delta);

    // Dragging the slider: stay 1:1 or it feels like lag, not polish.
    if (dist <= 4) {
      pos.current = chapter;
      setSwept(chapter);
      return;
    }

    const duration = Math.min(1500, 260 + dist * 1.15);
    const t0 = performance.now();

    const step = (now: number) => {
      if (playingRef.current) return; // play stole the float mid-tween
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      const v = from + delta * eased;
      pos.current = v;
      setSwept(v);
      raf.current = p < 1 ? requestAnimationFrame(step) : null;
    };

    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [chapter]);

  // playback loop
  useEffect(() => {
    playingRef.current = playing;
    if (!playing) return;
    if (raf.current !== null) cancelAnimationFrame(raf.current);

    let last = performance.now();
    const step = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000); // clamp tab-switch gaps
      last = now;
      const next = Math.min(world.chapterMax, pos.current + speed * BASE_CPS * dt);
      pos.current = next;
      setSwept(next);
      const fl = Math.max(world.chapterMin, Math.floor(next));
      setChapterState((c) => (c === fl ? c : fl));
      if (next >= world.chapterMax) {
        setPlaying(false);
        return;
      }
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [playing, speed, world.chapterMax, world.chapterMin]);

  const setChapter = useCallback(
    (ch: number) => {
      // any manual set is the reader taking the helm: playback yields first
      playingRef.current = false;
      setPlaying(false);
      setChapterState(clampChapter(world, ch));
    },
    [world],
  );

  const play = useCallback(() => {
    // sailing off the end restarts the voyage from chapter 1
    if (pos.current >= world.chapterMax) {
      pos.current = world.chapterMin;
      setSwept(world.chapterMin);
      setChapterState(world.chapterMin);
    }
    setPlaying(true);
  }, [world]);
  const pause = useCallback(() => setPlaying(false), []);

  return { chapter, swept, setChapter, playing, speed, setSpeed, play, pause };
}

/* -------------------------------------------------------------------------- */

type Props = {
  world: World;
  /** Phase 6 official art (slug -> /art/… url). Empty maps => SVG fallbacks. */
  art: Art;
  /** null = a cold visit with no ?ch= — show the hero. */
  initialChapter: number | null;
  initialAxis: Axis;
  /** The presence lens from ?lens= — "crew" on a plain load. */
  initialLens: PresenceLens;
  /** The shipwright's log — build provenance, rendered from the footer. */
  buildLog?: BuildLog;
};

const DEFAULT_CHAPTER = 1044;

export default function Atlas({ world, art, initialChapter, initialAxis, initialLens, buildLog }: Props) {
  const engine = useChapterEngine(world, initialChapter ?? DEFAULT_CHAPTER);
  const { chapter, swept, playing, speed } = engine;
  const [axis, setAxis] = useState<Axis>(initialAxis);
  const [hero, setHero] = useState(initialChapter === null);
  const [projection, setProjection] = useState<Projection>("globe");
  const [offCanon, setOffCanon] = useState(false);
  // The presence lens (Phase 6A). "crew" is Phase 5's who-sails-here coloring;
  // "fruit"/"haki" recolor the same chapter-gated entities by their revealed
  // powers; "off" hides the layer. At ch. 1 every lens shows exactly nothing.
  const [lens, setLens] = useState<PresenceLens>(initialLens);
  const [selected, setSelectedRaw] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  // Follow-cam: on by default — scrubbing or sailing keeps the ship in view.
  // Selecting an island or dragging the globe is the reader looking elsewhere.
  const [follow, setFollow] = useState(true);
  // The isolate filter + the search palette (Unit: identify & filter).
  const [focus, setFocusRaw] = useState<Focus | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  // Camera target for non-island search hits (crews have no selection slug).
  const [flyTarget, setFlyTarget] = useState<{ lng: number; lat: number; key: number } | null>(null);
  const flyKey = useRef(0);

  const setSelected = useCallback((slug: string | null) => {
    setSelectedRaw(slug);
    if (slug !== null) setFollow(false);
  }, []);

  // A fruit/haki focus drags the lens with it so the orb colors MEAN the
  // focused dimension; a crew focus needs presence visible at minimum.
  const setFocus = useCallback((f: Focus | null) => {
    setFocusRaw(f);
    if (!f) return;
    if (f.kind === "fruit") setLens("fruit");
    else if (f.kind === "haki") setLens("haki");
    else setLens((l) => (l === "off" ? "crew" : l));
  }, []);

  // The episode axis carries its own thumb position — see the note in
  // ChapterDock: episode -> chapter is many-to-one and would otherwise snap.
  const [episode, setEpisodeRaw] = useState(
    () => episodeForChapter(world, initialChapter ?? DEFAULT_CHAPTER) ?? world.episodeMax,
  );

  const shown = clampChapter(world, Math.round(swept));
  const at = useMemo(() => worldAtChapter(world, shown), [world, shown]);

  const setChapter = useCallback(
    (ch: number) => {
      const c = clampChapter(world, ch);
      engine.setChapter(c);
      setEpisodeRaw(episodeForChapter(world, c) ?? world.episodeMax);
    },
    [world, engine],
  );

  const setEpisode = useCallback(
    (ep: number) => {
      setEpisodeRaw(ep);
      engine.setChapter(chapterForEpisode(world, ep));
    },
    [world, engine],
  );

  // while sailing, the episode thumb follows the story (chapter is the truth)
  useEffect(() => {
    if (!playing) return;
    setEpisodeRaw(episodeForChapter(world, chapter) ?? world.episodeMax);
  }, [playing, chapter, world]);

  /* ------------------------------------------------------------------ url */
  useEffect(() => {
    if (hero) return;
    const t = setTimeout(() => {
      const q = new URLSearchParams();
      q.set("ch", String(chapter));
      if (axis === "episode") q.set("axis", "episode");
      if (lens !== "crew") q.set("lens", lens);
      window.history.replaceState(null, "", `?${q.toString()}`);
    }, 180);
    return () => clearTimeout(t);
  }, [chapter, axis, lens, hero]);

  /* -------------------------------------------------------------- keyboard */
  useEffect(() => {
    if (hero) return;
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      // Cmd/Ctrl+K opens search from anywhere (before the guards — it is a chord)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        return;
      }
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowLeft") setChapter(chapter - (e.shiftKey ? 25 : 1));
      else if (e.key === "ArrowRight") setChapter(chapter + (e.shiftKey ? 25 : 1));
      // a focused button owns Space (native activation) — don't double-fire
      else if (e.key === " " && !(el instanceof HTMLButtonElement)) (playing ? engine.pause : engine.play)();
      // Esc unwinds in order: filter first, then the selection
      else if (e.key === "Escape") (focus ? setFocus(null) : setSelected(null));
      else if (e.key === "/") setSearchOpen(true);
      else if (e.key.toLowerCase() === "g") setProjection((p) => (p === "globe" ? "mercator" : "globe"));
      else if (e.key.toLowerCase() === "f") setFollow((v) => !v);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chapter, hero, setChapter, playing, engine, focus, setFocus, setSelected]);

  const island = selected ? (world.islands.find((i) => i.slug === selected) ?? null) : null;

  // A search pick: islands select (the existing panel + easeTo); crews and
  // sailors isolate their crew and, when charted right now, fly the camera to
  // the active anchor. Any search fly is the reader looking away — follow off.
  const onSearchPick = useCallback(
    (h: SearchHit) => {
      if (h.kind === "island") {
        setSelected(h.slug);
        return;
      }
      // A warlord focuses on themselves (matchesFocus matches e.slug too);
      // a member focuses their whole crew.
      const crewSlug = h.kind === "member" ? h.crewSlug : h.slug;
      setFocus({ kind: "crew", slug: crewSlug });
      const roster = h.kind === "warlord" ? world.presence.characters : world.presence.crews;
      const entity = roster.find((c) => c.slug === crewSlug);
      const w = entity ? presenceWindowAt(entity.windows, shown) : null;
      if (w) {
        setFollow(false);
        flyKey.current += 1;
        setFlyTarget({ lng: w.lng, lat: w.lat, key: flyKey.current });
      }
    },
    [world, shown, setFocus, setSelected],
  );

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
          art={art}
          chapter={swept}
          projection={projection}
          showOffCanon={offCanon}
          lens={lens}
          selected={selected}
          onSelect={setSelected}
          follow={follow}
          onFollowBreak={() => setFollow(false)}
          focus={focus}
          flyTarget={flyTarget}
        />

        <SearchPalette
          world={world}
          shown={shown}
          offCanon={offCanon}
          open={searchOpen}
          onClose={() => setSearchOpen(false)}
          onPick={onSearchPick}
        />

        {/* masthead */}
        <div className="pointer-events-none absolute top-0 left-0 z-10 p-5">
          <div className="pointer-events-auto">
            <div className="font-pirate text-[17px] leading-none tracking-[0.06em] text-gold/90">
              {BRAND.name}
            </div>
            <p className="font-document mt-1 max-w-[230px] text-[11px] leading-snug text-muted-2 italic">
              {BRAND.tagline}
            </p>
          </div>
        </div>

        {/* left rail */}
        {!hero && (
          <aside className="gutter dr-fade absolute top-[74px] bottom-4 left-4 z-10 w-[290px] overflow-y-auto rounded-md border border-rope/70 bg-ink/88 shadow-2xl backdrop-blur">
            <Readout at={at} world={world} />
            {island && (
              <IslandDetail island={island} world={world} art={art} onClose={() => setSelected(null)} />
            )}
            <CrewRoster at={at} world={world} art={art} />

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
              <button
                type="button"
                onClick={() => setFollow((v) => !v)}
                title="Camera follows the ship (F)"
                className={[
                  "rounded-sm border bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] backdrop-blur transition-colors",
                  follow
                    ? "border-gold/60 text-gold"
                    : "border-rope text-muted-2 hover:border-gold/60 hover:text-gold",
                ].join(" ")}
              >
                ⌖ follow
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

            {/* The presence lens. One segmented control: "off" absorbs the old
                who-sails-here toggle; crews/fruit/haki pick what the orb colors
                MEAN. Every lens renders revealed facts only. */}
            <div className="max-w-[254px] rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] leading-snug tracking-[0.1em] text-muted-2 backdrop-blur">
              <div className="flex items-center gap-1">
                {(["off", "crew", "fruit", "haki"] as const).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLens(l)}
                    className={[
                      "rounded-sm border px-1.5 py-0.5 uppercase tracking-[0.14em] transition-colors",
                      lens === l
                        ? "border-gold/60 text-gold"
                        : "border-transparent text-muted-2 hover:text-muted",
                    ].join(" ")}
                  >
                    {l === "crew" ? "crews" : l}
                  </button>
                ))}
              </div>
              <div className="mt-1">
                {lens === "off" &&
                  "presence hidden — islands and the voyage only."}
                {lens === "crew" && (
                  <>
                    who sails here: {world.counts.presenceCrews} crews ·{" "}
                    {world.counts.presenceCharacters} Warlords. Chapter-gated, like everything
                    else.
                  </>
                )}
                {lens === "fruit" &&
                  "by devil fruit — orb colors follow the fruit's nature. Revealed fruits only; a fruit is a story reveal with its own chapter."}
                {lens === "haki" &&
                  "by haki — orb colors follow the highest revealed haki. Conqueror > Armament > Observation."}
              </div>
            </div>

            <Legend
              world={world}
              at={at}
              showOffCanon={offCanon}
              lens={lens}
              focus={focus}
              onFocus={setFocus}
            />
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
          playing={playing}
          speed={speed}
          onPlayPause={() => (playing ? engine.pause() : engine.play())}
          onSpeed={engine.setSpeed}
        />
      )}

      <Attribution world={world} buildLog={buildLog} />
    </div>
  );
}
