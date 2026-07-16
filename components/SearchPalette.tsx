"use client";

/**
 * components/SearchPalette.tsx — spoiler-safe search (Cmd+K or /).
 *
 * SPOILER SAFETY IS CONSTRUCTIVE, NOT COSMETIC: the index is built only while
 * the palette is open, and an entry past the reader's chapter is never
 * constructed at all — no hidden rows, no filtered-out DOM, nothing for a
 * curious inspector to find. Search can never leak a future name because the
 * future name never exists here.
 *
 *   islands     status=manga, debut <= chapter (+ off-canon while that layer
 *               is on — they are chapterless by design)
 *   crews       first presence window from <= chapter
 *   warlords    same
 *   members     joined (fromChapter <= chapter); selecting one isolates their crew
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { World } from "@/lib/canon";
import { presenceWindowAt } from "@/lib/canon";

export type SearchHit =
  | { kind: "island"; slug: string; label: string; sub: string }
  | { kind: "crew" | "warlord"; slug: string; label: string; sub: string; charted: boolean }
  | { kind: "member"; slug: string; label: string; sub: string; crewSlug: string; charted: boolean };

type Props = {
  world: World;
  /** The reader's (rounded, clamped) chapter — the gate every entry passes. */
  shown: number;
  offCanon: boolean;
  open: boolean;
  onClose: () => void;
  onPick: (hit: SearchHit) => void;
};

const KIND_LABEL: Record<SearchHit["kind"], string> = {
  island: "island",
  crew: "crew",
  warlord: "warlord",
  member: "pirate",
};

export default function SearchPalette({ world, shown, offCanon, open, onClose, onPick }: Props) {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Built on open, gated at construction. useMemo keyed on the gate inputs so
  // scrubbing with the palette open re-gates live (backward scrub un-indexes).
  const index = useMemo<SearchHit[]>(() => {
    if (!open) return [];
    const out: SearchHit[] = [];
    for (const i of world.islands) {
      if (i.status === "manga" && i.debutChapter !== null && i.debutChapter <= shown) {
        out.push({ kind: "island", slug: i.slug, label: i.name, sub: i.sea ?? "charted" });
      } else if (offCanon && i.status !== "manga") {
        out.push({ kind: "island", slug: i.slug, label: i.name, sub: "off-canon" });
      }
    }
    for (const c of world.presence.crews) {
      if (!c.windows.some((w) => w.fromChapter <= shown)) continue;
      const active = presenceWindowAt(c.windows, shown);
      out.push({
        kind: "crew", slug: c.slug, label: c.name, charted: !!active,
        sub: active ? active.label : "not currently charted",
      });
      for (const m of c.members) {
        if (m.fromChapter > shown) continue;
        out.push({
          kind: "member", slug: m.slug, label: m.name, crewSlug: c.slug, charted: !!active,
          sub: c.name,
        });
      }
    }
    for (const c of world.presence.characters) {
      if (!c.windows.some((w) => w.fromChapter <= shown)) continue;
      const active = presenceWindowAt(c.windows, shown);
      out.push({
        kind: "warlord", slug: c.slug, label: c.name, charted: !!active,
        sub: active ? active.label : "not currently charted",
      });
    }
    return out;
  }, [open, world, shown, offCanon]);

  const hits = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return [];
    const starts: SearchHit[] = [];
    const contains: SearchHit[] = [];
    for (const e of index) {
      const l = e.label.toLowerCase();
      if (l.startsWith(needle)) starts.push(e);
      else if (l.includes(needle)) contains.push(e);
      if (starts.length >= 12) break;
    }
    return [...starts, ...contains].slice(0, 12);
  }, [index, q]);

  useEffect(() => {
    if (open) {
      setQ("");
      setCursor(0);
      // focus after the overlay mounts
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => setCursor(0), [q]);

  if (!open) return null;

  const pick = (h: SearchHit) => {
    onPick(h);
    onClose();
  };

  return (
    <div
      className="absolute inset-0 z-30 bg-abyss/40 backdrop-blur-[2px]"
      onMouseDown={onClose}
    >
      <div
        className="mx-auto mt-[14vh] w-[420px] overflow-hidden rounded-md border border-rope bg-ink/95 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            else if (e.key === "ArrowDown") setCursor((c) => Math.min(hits.length - 1, c + 1));
            else if (e.key === "ArrowUp") setCursor((c) => Math.max(0, c - 1));
            else if (e.key === "Enter" && hits[cursor]) pick(hits[cursor]);
            else return;
            e.preventDefault();
            e.stopPropagation();
          }}
          placeholder={`Search the charted world (ch. ${shown})…`}
          className="w-full border-b border-rope/60 bg-transparent px-4 py-3 font-mono text-[12px] text-parchment placeholder:text-muted-2 focus:outline-none"
          spellCheck={false}
        />
        {q.trim() && (
          <ul className="max-h-[320px] overflow-y-auto py-1">
            {hits.length === 0 && (
              <li className="px-4 py-3 text-[11px] text-muted-2">
                Nothing by that name on your chart yet.
              </li>
            )}
            {hits.map((h, i) => (
              <li key={`${h.kind}:${h.slug}`}>
                <button
                  type="button"
                  onClick={() => pick(h)}
                  onMouseEnter={() => setCursor(i)}
                  className={[
                    "flex w-full items-baseline justify-between gap-3 px-4 py-2 text-left transition-colors",
                    i === cursor ? "bg-gold/10" : "",
                  ].join(" ")}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[12px] text-parchment">{h.label}</span>
                    <span className="block truncate text-[10px] text-muted-2">{h.sub}</span>
                  </span>
                  <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.14em] text-muted-2">
                    {KIND_LABEL[h.kind]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="border-t border-rope/60 px-4 py-1.5 font-mono text-[9px] uppercase tracking-[0.14em] text-muted-2">
          Results stop at chapter {shown} — search cannot read ahead for you.
        </div>
      </div>
    </div>
  );
}
