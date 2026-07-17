/**
 * lib/og-fonts.ts — the OG cards' font bytes.
 *
 * SERVER ONLY (node:fs). Module-cached like loadCanon/loadArt: read once per
 * process, not once per card.
 *
 * These are vendored .ttf files rather than next/font's output because
 * ImageResponse (Satori) reads ttf/otf/woff and next/font emits content-hashed
 * woff2. See assets/fonts/README.md. `assets/`, not `public/` — the browser
 * never asks for these; only the OG route does.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";

export type OgFont = {
  name: string;
  data: ArrayBuffer;
  weight: 400;
  style: "normal";
};

let cached: OgFont[] | null = null;

export async function ogFonts(): Promise<OgFont[]> {
  if (cached) return cached;
  const dir = join(process.cwd(), "assets", "fonts");
  const [pirata, fell] = await Promise.all([
    readFile(join(dir, "PirataOne-Regular.ttf")),
    readFile(join(dir, "IMFellEnglish-Regular.ttf")),
  ]);
  cached = [
    // The names Satori matches on in fontFamily — they are not the CSS vars.
    { name: "Pirata One", data: toArrayBuffer(pirata), weight: 400, style: "normal" },
    { name: "IM Fell English", data: toArrayBuffer(fell), weight: 400, style: "normal" },
  ];
  return cached;
}

function toArrayBuffer(b: Buffer): ArrayBuffer {
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
}
