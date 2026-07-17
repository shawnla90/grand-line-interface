"use client";

import { useEffect, useRef, useState } from "react";

/**
 * OrbitControls — the only chrome grab-and-spin needs.
 *
 * Shown only while you are orbiting a dived-into 3D island (WorldMap owns that
 * state). It does two small things: tell you the drag changed meaning the first
 * time it happens, and give you a way back to level. Everything else — the actual
 * bearing/pitch drag — is pointer handling on the canvas, not here.
 */
export function OrbitControls({ orbiting, onLevel }: { orbiting: boolean; onLevel: () => void }) {
  // Show the hint the first time orbit mode engages in a session, then never
  // again — it is a "the drag does something different now" nudge, not a label.
  const [hintDone, setHintDone] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (orbiting && !hintDone) {
      setShowHint(true);
      setHintDone(true);
      timer.current = setTimeout(() => setShowHint(false), 3600);
    }
    if (!orbiting) setShowHint(false);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [orbiting, hintDone]);

  if (!orbiting) return null;

  return (
    <div className="pointer-events-none absolute bottom-6 left-1/2 z-[7] flex -translate-x-1/2 flex-col items-center gap-2">
      {showHint && (
        <div className="rounded-full border border-rope/60 bg-ink/90 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 shadow-lg backdrop-blur">
          drag to orbit · up/down to tilt
        </div>
      )}
      <button
        type="button"
        onClick={onLevel}
        className="pointer-events-auto rounded-full border border-rope bg-ink/85 px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-parchment shadow-lg backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
      >
        ↺ level view
      </button>
    </div>
  );
}
