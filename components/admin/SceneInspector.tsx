"use client";

/**
 * components/admin/SceneInspector.tsx — why is this scene not on screen?
 *
 * DEV-ONLY. Every row is the registry's own answer, not a re-derivation: it
 * calls sceneVisibilityAt, so if this page and the map ever disagree, one of
 * them is lying and it is not this one.
 */

import { useState } from "react";
import {
  sceneVisibilityAt, routeGeometryPolicy,
  type NarrativeScene, type SceneHiddenReason,
} from "@/lib/scenes";
import { Kicker, Panel } from "@/components/ui/Panel";

const REASON_COPY: Record<SceneHiddenReason, string> = {
  chapter_locked: "the reader has not reached it",
  gate_unverified: "nobody has confirmed the chapter",
  asset_not_ready: "no finished asset backs it",
  projection_unsupported: "the globe uses the flat fallback",
  distance_lod: "too far away to be worth loading",
};

export default function SceneInspector({
  scenes,
  warnings,
  chapter: initial,
}: {
  scenes: NarrativeScene[];
  warnings: string[];
  chapter: number;
}) {
  const [chapter, setChapter] = useState(initial);
  const [projection, setProjection] = useState<"globe" | "mercator">("mercator");

  return (
    <main className="min-h-dvh px-6 py-8">
      <Kicker>Narrative scene registry — dev only</Kicker>
      <h1 className="font-pirate mt-2 text-[32px] leading-none text-parchment">
        Why is this scene not on screen?
      </h1>
      <p className="font-document mt-2 max-w-[720px] text-[13px] leading-relaxed text-muted">
        Data only. Nothing here loads an asset. Scrub to <span className="text-parchment">322</span> and{" "}
        <span className="text-parchment">323</span> to watch Water 7&apos;s base gate outrank its own
        earliest variant; to <span className="text-parchment">239</span> for Skypiea&apos;s tie.
      </p>

      <div className="mt-5 flex items-center gap-4">
        <input
          type="range"
          min={1}
          max={1185}
          value={chapter}
          onChange={(e) => setChapter(Number(e.target.value))}
          className="dial w-[420px]"
        />
        <span className="tnum font-mono text-[13px] text-gold">ch. {chapter}</span>
        <button
          type="button"
          onClick={() => setProjection((p) => (p === "globe" ? "mercator" : "globe"))}
          className="rounded-sm border border-rope px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-2 hover:text-gold"
        >
          {projection}
        </button>
      </div>

      {warnings.map((w) => (
        <p key={w} className="mt-4 max-w-[860px] rounded-sm border border-straw/30 bg-straw/5 px-3 py-2 text-[11px] leading-snug text-muted">
          <span className="text-straw">!</span> {w}
        </p>
      ))}

      <div className="mt-6 space-y-2">
        {scenes.map((s) => {
          const v = sceneVisibilityAt(s, { chapter, projection, distanceLod: "near" });
          const route = routeGeometryPolicy(s);
          return (
            <Panel key={s.id} className="px-4 py-3">
              <div className="flex items-baseline justify-between gap-4">
                <div className="min-w-0">
                  <span className="font-mono text-[12px] text-parchment">{s.id}</span>
                  {v.movingAnchor && (
                    <span className="ml-2 rounded-sm border border-gold-dim px-1 font-mono text-[8px] uppercase tracking-[0.12em] text-gold-2">
                      moving anchor
                    </span>
                  )}
                  {route && (
                    <span
                      title={route.note}
                      className="ml-2 rounded-sm border border-rope-2 px-1 font-mono text-[8px] uppercase tracking-[0.12em] text-muted-2"
                    >
                      {route.label}
                    </span>
                  )}
                  <div className="mt-0.5 text-[11px] text-muted-2">{s.label}</div>
                </div>
                <span
                  className={`shrink-0 font-mono text-[10px] uppercase tracking-[0.14em] ${
                    v.visible ? "text-gold" : "text-muted-2"
                  }`}
                >
                  {v.visible ? "visible" : "hidden"}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap gap-1.5">
                {v.reasons.map((r) => (
                  <span
                    key={r}
                    title={REASON_COPY[r]}
                    className="rounded-sm border border-straw/40 bg-straw/5 px-1.5 py-px font-mono text-[9px] text-straw"
                  >
                    {r}
                  </span>
                ))}
                {v.state && (
                  <span className="rounded-sm border border-rope-2 px-1.5 py-px font-mono text-[9px] text-muted">
                    state: {v.state.id}
                  </span>
                )}
                {v.events.map((e) => (
                  <span key={e.id} className="rounded-sm border border-rope px-1.5 py-px font-mono text-[9px] text-muted-2">
                    event: {e.id}
                  </span>
                ))}
              </div>

              {(v.suppressed.variants.length > 0 || v.suppressed.events.length > 0) && (
                <div className="mt-2 border-t border-rope/50 pt-2">
                  <span className="font-mono text-[8px] uppercase tracking-[0.14em] text-muted-2">
                    withheld
                  </span>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {[...v.suppressed.variants, ...v.suppressed.events].map((x) => (
                      <span key={x.id} className="font-mono text-[9px] text-muted-2/70">
                        {x.id} <span className="text-straw/60">({x.reason})</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </main>
  );
}
