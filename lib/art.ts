/**
 * lib/art.ts — the Phase 6 art loader. Server-only (node:fs).
 *
 * Reads data/generated/art_manifest.json (produced by scripts/sync_art.py) and
 * turns it into slug->url lookups the UI can consume. The URLs are plain
 * "/art/…" strings served from public/, so the resulting Art object is safe to
 * hand to a "use client" component as a prop.
 *
 * ART IS OPTIONAL. Every mark on the map has an original-SVG fallback, so a
 * missing manifest (or a takedown that deletes public/art/) must NOT break the
 * build — loadArt() just returns empty maps and the app falls back to SVG. That
 * is the whole point of keeping the marks in code: the art is an enhancement
 * layer, never a dependency.
 *
 * LICENSE: the files these URLs point at are © Oda/Shueisha/Toei, excluded from
 * this repo's MIT license. See public/art/README.md.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

const ArtImage = z.object({
  kind: z.string(),
  slug: z.string(),
  ref_id: z.number().int().nullable().optional(),
  file: z.string(), // e.g. "art/characters/monkey-d-luffy.webp"
});

const ArtManifest = z.object({
  images: z.array(ArtImage),
});

/** slug -> "/art/…url"; fruits keyed by the canon fruit id (characters carry fruit_id). */
export type Art = {
  characters: Record<string, string>;
  flags: Record<string, string>;
  ships: Record<string, string>;
  islands: Record<string, string>;
  fruits: Record<number, string>;
  /** How many attributed images loaded — 0 means the app is running on SVG fallbacks. */
  count: number;
};

const EMPTY: Art = { characters: {}, flags: {}, ships: {}, islands: {}, fruits: {}, count: 0 };

const MANIFEST_PATH = join(process.cwd(), "data", "generated", "art_manifest.json");

let cached: Art | null = null;

export function loadArt(): Art {
  if (cached) return cached;

  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(MANIFEST_PATH, "utf8"));
  } catch {
    // No manifest = Phase 6 art not present. Fall back to SVG marks, silently.
    cached = EMPTY;
    return cached;
  }

  const parsed = ArtManifest.safeParse(raw);
  if (!parsed.success) {
    // A malformed manifest should not take the site down — the art is optional.
    console.warn("[art] art_manifest.json failed to parse; running on SVG fallbacks");
    cached = EMPTY;
    return cached;
  }

  const art: Art = { characters: {}, flags: {}, ships: {}, islands: {}, fruits: {}, count: 0 };
  for (const img of parsed.data.images) {
    const url = "/" + img.file.replace(/^\/+/, "");
    art.count++;
    switch (img.kind) {
      case "characters":
        art.characters[img.slug] = url;
        break;
      case "flags":
        art.flags[img.slug] = url;
        break;
      case "ships":
        art.ships[img.slug] = url;
        break;
      case "islands":
        art.islands[img.slug] = url;
        break;
      case "fruits":
        if (typeof img.ref_id === "number") art.fruits[img.ref_id] = url;
        break;
      default:
        break; // unknown kind — ignore rather than throw; art is best-effort
    }
  }

  cached = art;
  return cached;
}
