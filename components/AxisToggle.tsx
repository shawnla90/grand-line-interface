"use client";

/**
 * components/AxisToggle.tsx — read the manga, or watch the anime.
 *
 * Chapters are the spine; episodes are a derived, lossy view of them (98 episodes
 * adapt no manga at all, and the anime currently trails the manga by ~53
 * chapters). Switching axis never changes the underlying state — it only changes
 * which number you are shown and which one you can type.
 */

import type { Axis } from "@/lib/canon";

export default function AxisToggle({
  axis,
  onAxis,
  size = "dock",
}: {
  axis: Axis;
  onAxis: (a: Axis) => void;
  size?: "hero" | "dock";
}) {
  const hero = size === "hero";
  return (
    <div
      role="tablist"
      aria-label="Read by chapter or episode"
      className="inline-flex rounded-sm border border-rope p-0.5"
    >
      {(["chapter", "episode"] as const).map((a) => {
        const on = axis === a;
        return (
          <button
            key={a}
            role="tab"
            aria-selected={on}
            type="button"
            onClick={() => onAxis(a)}
            className={[
              "rounded-[2px] font-mono uppercase tracking-[0.18em] transition-colors",
              hero ? "px-3 py-1.5 text-[10px]" : "px-2 py-1 text-[9px]",
              on ? "bg-gold/90 text-abyss" : "text-muted-2 hover:text-parchment",
            ].join(" ")}
          >
            {a}
          </button>
        );
      })}
    </div>
  );
}
