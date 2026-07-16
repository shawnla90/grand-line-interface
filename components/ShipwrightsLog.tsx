"use client";

/**
 * components/ShipwrightsLog.tsx — build provenance, rendered.
 *
 * The atlas puts a confidence on every pin; this puts one on the codebase.
 * Which AI model built each phase, under which harness, with the commit stamps
 * to check it against `git log`. Plain DOM only — no MapLibre import — so it
 * renders identically when WebGL is unavailable and the map has degraded.
 */

import { useEffect } from "react";
import type { BuildLogEntry } from "@/lib/buildlog";

export default function ShipwrightsLog({
  entries,
  onClose,
}: {
  entries: BuildLogEntry[];
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-abyss/80 p-6 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Shipwright's log"
    >
      <div
        className="dr-fade max-h-[80vh] w-full max-w-[560px] overflow-y-auto rounded-md border border-rope bg-ink/97 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-baseline justify-between gap-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold/85">
            Shipwright&apos;s log
          </div>
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
          >
            close
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          Who built this — by phase, by model, by harness. The atlas puts a confidence on every
          pin; this is the same honesty applied to the code itself.
        </p>

        <ul className="mt-4 space-y-3">
          {entries.map((e) => (
            <li key={e.phase} className="border-t border-rope/50 pt-3">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-2">
                  Phase {e.phase}
                </span>
                <span className="font-mono text-[10px] text-muted-2">{e.role}</span>
              </div>
              <div className="mt-0.5 text-[12px] text-parchment">{e.title}</div>
              <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                <span className="text-[11px] text-gold">{e.builder}</span>
                <span className="font-mono text-[10px] text-muted-2">{e.harness}</span>
                {e.commits.length > 0 && (
                  <span className="tnum font-mono text-[10px] text-muted-2/80">
                    {e.commits.join(" · ")}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>

        <p className="mt-4 border-t border-rope/50 pt-3 text-[10px] leading-relaxed text-muted-2">
          Phases 1–4 were built by Claude Opus 4.8 running ultracode. The Phase 5 plan was drafted
          by a Codex session; Phase 5 onward is built by Claude Fable 5 in Claude Code. Commit
          stamps are checkable against <span className="font-mono">git log</span> — provenance is
          part of the product.
        </p>
      </div>
    </div>
  );
}
