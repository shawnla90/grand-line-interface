"use client";

/**
 * components/admin/PlaceEditor.tsx — the /admin/place tool (dev-only).
 *
 * The durable way to make island positions fan-accurate: pick an island (worst
 * confidence first), click the chart where it belongs, and the position is written
 * straight into canon/islands.coords.json with confidence "canon". The pin jumps
 * on the map immediately (WorldMap re-reads its island source), and the change is
 * a one-line git diff a contributor could PR.
 *
 * Keys: [n] next island · [1] guess · [2] derived · [3] canon (sets the confidence
 * the NEXT click will write). Click the map to place the selected island.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import WorldMap from "@/components/WorldMap";
import type { World, Confidence } from "@/lib/canon";

const RANK: Record<Confidence, number> = { guess: 0, derived: 1, canon: 2 };
const BADGE: Record<Confidence, string> = {
  guess: "text-fog",
  derived: "text-gold",
  canon: "text-parchment",
};

export default function PlaceEditor({ world: initial }: { world: World }) {
  const [world, setWorld] = useState(initial);
  const [target, setTarget] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<Confidence>("canon");
  const [note, setNote] = useState("Pick an island, then click the chart to place it.");
  const [saving, setSaving] = useState(false);

  // The mappable set, worst confidence first — the pins that most need a human.
  const ordered = useMemo(
    () =>
      world.islands
        .filter((i) => i.status === "manga" && i.debutChapter !== null)
        .sort((a, b) => RANK[a.confidence] - RANK[b.confidence] || a.slug.localeCompare(b.slug)),
    [world.islands],
  );

  const done = ordered.filter((i) => i.confidence === "canon").length;

  const place = useCallback(
    async (lngLat: [number, number]) => {
      if (!target) {
        setNote("Select an island from the list first.");
        return;
      }
      setSaving(true);
      try {
        const res = await fetch("/api/place", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ slug: target, lng: lngLat[0], lat: lngLat[1], confidence }),
        });
        const j = await res.json();
        if (!res.ok) {
          setNote(`error: ${j.error ?? res.status}`);
          return;
        }
        setWorld((w) => ({
          ...w,
          islands: w.islands.map((i) =>
            i.slug === target ? { ...i, lng: j.lng, lat: j.lat, confidence: confidence } : i,
          ),
        }));
        setNote(`✓ ${target} → ${j.lng}, ${j.lat} (${confidence})`);
        // Advance to the next island that still needs a human.
        const idx = ordered.findIndex((i) => i.slug === target);
        const next = ordered.slice(idx + 1).find((i) => i.confidence !== "canon");
        setTarget(next?.slug ?? null);
      } catch (e) {
        setNote(`network error: ${String(e)}`);
      } finally {
        setSaving(false);
      }
    },
    [target, confidence, ordered],
  );

  // Keyboard: n = next, 1/2/3 = confidence to write.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "n") {
        const idx = ordered.findIndex((i) => i.slug === target);
        setTarget(ordered[(idx + 1) % ordered.length]?.slug ?? null);
      } else if (e.key === "1") setConfidence("guess");
      else if (e.key === "2") setConfidence("derived");
      else if (e.key === "3") setConfidence("canon");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ordered, target]);

  return (
    <div className="flex h-screen bg-ink text-parchment">
      <aside className="flex w-[300px] flex-col border-r border-rope/60">
        <div className="border-b border-rope/60 px-4 py-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold">/admin/place</div>
          <div className="mt-1 text-[12px] text-muted">
            {done}/{ordered.length} confirmed · dev-only, writes canon/
          </div>
          {/* This tool is open. The maintainer is not hand-routing every island —
              it exists so the community can. */}
          <div className="mt-2 rounded border border-rope/50 bg-rope/10 px-2.5 py-2 text-[11px] leading-relaxed text-muted">
            <span className="text-parchment">Contributions welcome.</span> The positions are close,
            not hand-verified. If you know where an island belongs, place it — each pin is a clean
            one-line diff you can open as a PR. See <span className="font-mono text-gold">README →
            Contributing</span>.
          </div>
          <div className="mt-2 min-h-[16px] font-mono text-[10px] text-muted-2">{note}</div>
          <div className="mt-2 flex gap-1">
            {(["guess", "derived", "canon"] as Confidence[]).map((c, i) => (
              <button
                key={c}
                onClick={() => setConfidence(c)}
                className={`rounded border px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide ${
                  confidence === c ? "border-gold text-gold" : "border-rope/60 text-muted-2"
                }`}
              >
                {i + 1} {c}
              </button>
            ))}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {ordered.map((i) => (
            <button
              key={i.slug}
              onClick={() => setTarget(i.slug)}
              className={`flex w-full items-center justify-between px-4 py-1.5 text-left text-[12px] ${
                target === i.slug ? "bg-rope/30 text-parchment" : "text-muted hover:bg-rope/10"
              }`}
            >
              <span className="truncate">{i.name}</span>
              <span className={`ml-2 font-mono text-[9px] uppercase ${BADGE[i.confidence]}`}>
                {i.confidence}
              </span>
            </button>
          ))}
        </div>
      </aside>

      <div className="relative flex-1">
        <WorldMap
          world={world}
          chapter={world.chapterMax}
          projection="mercator"
          showOffCanon
          selected={target}
          onSelect={setTarget}
          placingSlug={target}
          onPlaceAt={place}
        />
        {saving && (
          <div className="pointer-events-none absolute right-4 top-4 z-20 rounded bg-ink/90 px-2 py-1 font-mono text-[10px] text-gold">
            saving…
          </div>
        )}
      </div>
    </div>
  );
}
