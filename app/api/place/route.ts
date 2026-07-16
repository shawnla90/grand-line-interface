/**
 * app/api/place/route.ts — the write half of /admin/place.
 *
 * DEV-ONLY. This is the sanctioned human-authoring path into canon/ (the file is
 * human-owned; a *sync/build* script writing here is the bug, not a person placing
 * a pin). It refuses to run in production so it can never ship in a deployed build,
 * and it only ever touches canon/islands.coords.json.
 *
 * A placement is a human confirming a position, so it writes canon_confidence:
 * "canon" and a hand-authored source_ref. Git is the database — every write is a
 * readable one-line diff a contributor could open as a PR.
 */

import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { NextResponse } from "next/server";

const COORDS = join(process.cwd(), "canon", "islands.coords.json");

const CONFIDENCE = new Set(["canon", "derived", "guess"]);

export async function POST(req: Request) {
  if (process.env.NODE_ENV === "production") {
    return new NextResponse("Not found", { status: 404 });
  }

  let body: { slug?: string; lng?: number; lat?: number; confidence?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad JSON" }, { status: 400 });
  }

  const { slug, lng, lat } = body;
  const confidence = body.confidence ?? "canon";
  if (!slug || typeof lng !== "number" || typeof lat !== "number") {
    return NextResponse.json({ error: "slug, lng, lat required" }, { status: 400 });
  }
  if (!CONFIDENCE.has(confidence)) {
    return NextResponse.json({ error: `bad confidence ${confidence}` }, { status: 400 });
  }

  const doc = JSON.parse(await readFile(COORDS, "utf8"));
  const row = doc.islands.find((x: { slug: string }) => x.slug === slug);
  if (!row) {
    return NextResponse.json({ error: `unknown island ${slug}` }, { status: 404 });
  }

  // Mutate only this island's four fields, in place — so a placement is a clean,
  // ~4-line git diff a contributor can read and PR. The sea is untouched (the
  // editor never moves an island between seas), so _counts stays valid as-is.
  row.lng = Math.round(lng * 1e4) / 1e4;
  row.lat = Math.round(lat * 1e4) / 1e4;
  row.canon_confidence = confidence;
  row.source_ref = "Hand-placed via /admin/place — a human confirmed this position on the chart.";

  await writeFile(COORDS, JSON.stringify(doc, null, 2) + "\n", "utf8");

  return NextResponse.json({ ok: true, slug, lng: row.lng, lat: row.lat, confidence });
}
