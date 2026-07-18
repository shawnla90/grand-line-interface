"use client";

import { useEffect, useRef, useState } from "react";

/**
 * OrbitControls — the chrome for hold-to-orbit.
 *
 * A plain drag pans; to rotate you press and HOLD on an island, which locks it as
 * the pivot and orbits around it (WorldMap owns that gesture). This shows two
 * things: a "◎ orbiting <island>" caption while you are holding, and a "↺ level
 * view" button whenever the camera is left tilted or turned, so you can straighten
 * back up. The first time you orbit in a session it also nudges how the gesture
 * works, then never again.
 */
export function OrbitControls({
  orbitTarget,
  tilted,
  onLevel,
}: {
  orbitTarget: string | null;
  tilted: boolean;
  onLevel: () => void;
}) {
  const [hintDone, setHintDone] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (orbitTarget && !hintDone) {
      setShowHint(true);
      setHintDone(true);
      timer.current = setTimeout(() => setShowHint(false), 3600);
    }
    if (!orbitTarget) setShowHint(false);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [orbitTarget, hintDone]);

  if (!orbitTarget && !tilted) return null;

  return (
    <div className="pointer-events-none absolute bottom-6 left-1/2 z-[7] flex -translate-x-1/2 flex-col items-center gap-2">
      {orbitTarget && (
        <div className="rounded-full border border-gold/50 bg-ink/90 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-gold shadow-lg backdrop-blur">
          ◎ orbiting {orbitTarget}
        </div>
      )}
      {showHint && (
        <div className="rounded-full border border-rope/60 bg-ink/90 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 shadow-lg backdrop-blur">
          drag to spin · up/down to tilt · release to pan
        </div>
      )}
      {tilted && !orbitTarget && (
        <button
          type="button"
          onClick={onLevel}
          className="pointer-events-auto rounded-full border border-rope bg-ink/85 px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-parchment shadow-lg backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
        >
          ↺ level view
        </button>
      )}
    </div>
  );
}
