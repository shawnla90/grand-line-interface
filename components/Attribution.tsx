"use client";

/**
 * components/Attribution.tsx — the footer. Small, honest, non-negotiable.
 *
 * data/canon.json carries meta.attribution_required_in_ui: true. The Fandom wiki
 * is CC-BY-SA 3.0: the FACTS (chapter numbers, episode ranges, island debuts) are
 * not copyrightable and are free to use, but attribution is the obligation and it
 * is cheap to honour. No article prose is reproduced anywhere in this app.
 *
 * The build fingerprint is here on purpose. This is a dataset with a version, and
 * a reference work that will not tell you which version you are reading is not
 * much of a reference work.
 */

import type { World } from "@/lib/canon";
import { BRAND } from "@/config/brand";

export default function Attribution({ world }: { world: World }) {
  const built = new Date(world.meta.generatedAt);
  const stamp = Number.isNaN(built.getTime())
    ? world.meta.generatedAt
    : built.toISOString().slice(0, 10);

  return (
    <footer className="pointer-events-auto border-t border-rope/40 bg-abyss px-6 py-2.5">
      <div className="mx-auto flex max-w-[1180px] flex-col gap-1.5 text-[10px] leading-relaxed text-muted-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-[760px]">
          {BRAND.legal.copyright} {BRAND.legal.unofficial} Facts from{" "}
          {BRAND.legal.sources.map((s, i) => (
            <span key={s.label}>
              <a
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted underline underline-offset-2 transition-colors hover:text-gold"
              >
                {s.label}
              </a>
              {i < BRAND.legal.sources.length - 1 ? " and " : ""}
            </span>
          ))}
          . Wiki facts used under CC&#8209;BY&#8209;SA&nbsp;3.0; no article prose is reproduced.
        </p>

        <p className="tnum shrink-0 font-mono text-muted-2/80">
          canon {stamp} · {world.meta.sourceManifestSha.slice(0, 7)}
        </p>
      </div>
    </footer>
  );
}
