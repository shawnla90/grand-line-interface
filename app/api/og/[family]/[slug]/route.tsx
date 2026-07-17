/**
 * app/api/og/[family]/[slug]/route.tsx — the share card, stamped with the
 * sharer's chapter.
 *
 * ============================================================================
 * WHY A ROUTE HANDLER AND NOT opengraph-image.tsx
 * ============================================================================
 * The file convention CANNOT do this job. Its default export receives `params`
 * only — no `searchParams` (see next/dist/docs .../opengraph-image.md). The
 * whole requirement is "the card is stamped with the sharer's chapter", and the
 * chapter lives in ?ch=. So the card is a route, and generateMetadata points
 * openGraph.images at it with the chapter already baked into the URL.
 *
 * NODE RUNTIME, not edge: loadCanon() uses node:fs on a 1.9MB artifact. Railway
 * is a Node server. (This is one of the three things a future Cloudflare move
 * has to answer — noted in the phase plan, not solved here.)
 *
 * THE SAME GATE AS THE PAGE. A card is the most public surface in the product:
 * it renders in a group chat, in a timeline, in a crawler's cache. An unfogged
 * card under a fogged page would leak to strangers who never clicked. So the
 * uncharted card is a FIXED image — it never contains the slug, so a share of
 * /island/laugh-tale?ch=100 previews exactly like a share of a typo.
 */

import { ImageResponse } from "next/og";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import {
  characterEntry, crewEntry, fruitEntry, islandEntry, isEntryFamily, readChapter,
  type ChapterCtx, type EntryFamily,
} from "@/lib/entry";
import { bountyAt } from "@/lib/canon";
import { ogFonts } from "@/lib/og-fonts";
import { BRAND } from "@/config/brand";

const W = 1200;
const H = 630;

const INK = { bg: "#060b16", panel: "#0a1120", rope: "#1d2941", parchment: "#efe6d4",
              muted: "#8c9ab5", muted2: "#5b6880", gold: "#e3b04b" };

type Card = { kicker: string; title: string; sub: string | null; figure: string | null };

/** One shape for every family, so the layout cannot leak by branching. */
function resolve(family: EntryFamily, slug: string, ctx: ChapterCtx): Card | null {
  const canon = loadCanon();
  const world = buildWorld(canon);
  if (family === "island") {
    const e = islandEntry(world, slug, ctx);
    return e.state === "charted"
      ? { kicker: "Island", title: e.data.island.name, sub: e.data.island.sea, figure: null }
      : null;
  }
  if (family === "character") {
    const e = characterEntry(canon, slug, ctx);
    if (e.state !== "charted") return null;
    const b = bountyAt(e.data.poster.bountyHistory, ctx.chapter);
    return {
      kicker: "Wanted",
      title: e.data.poster.name,
      sub: e.data.poster.epithet,
      // NOT formatBerry: Pirata One has no ฿ glyph and Satori renders tofu for
      // it. The card spells the unit instead — a poster says BERRIES anyway.
      figure: b ? `${b.amount.toLocaleString("en-US")} berries` : "no bounty posted yet",
    };
  }
  if (family === "crew") {
    const e = crewEntry(world, slug, ctx);
    return e.state === "charted"
      ? { kicker: "Crew", title: e.data.name, sub: e.data.here?.label ?? null, figure: null }
      : null;
  }
  const e = fruitEntry(canon, world, slug, ctx);
  return e.state === "charted"
    ? { kicker: "Devil fruit", title: e.data.name, sub: e.data.type, figure: null }
    : null;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ family: string; slug: string }> },
) {
  const world = buildWorld(loadCanon());
  const { family, slug } = await params;
  const sp = Object.fromEntries(new URL(req.url).searchParams);
  const ctx = readChapter(world, sp);
  // A bad family is uncharted, not a 400: an error page here would be an oracle
  // of a different kind, and a broken preview is worse than a fogged one.
  const card = isEntryFamily(family) ? resolve(family, slug, ctx) : null;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column",
          justifyContent: "center", padding: "72px 80px", background: INK.bg,
          backgroundImage: `radial-gradient(1000px 500px at 15% -10%, #0d2036 0%, ${INK.bg} 70%)`,
          border: `2px solid ${INK.rope}`,
        }}
      >
        {/* ONE element, always — a fragment here collapses under Satori and the
            whole card lays out as a single row. Every div with more than one
            child carries an explicit display:flex for the same reason. */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontFamily: "IM Fell English", fontSize: 22, letterSpacing: 6,
                        textTransform: "uppercase", color: card ? INK.gold : INK.muted2 }}>
            {card ? card.kicker : "Uncharted"}
          </div>
          <div style={{ fontFamily: "Pirata One", fontSize: card ? 92 : 96, lineHeight: 1.05,
                        color: INK.parchment, marginTop: 14 }}>
            {card ? card.title : "Beyond your chapter"}
          </div>
          <div style={{ fontFamily: "IM Fell English", fontSize: 30, color: INK.muted,
                        marginTop: 10, fontStyle: "italic" }}>
            {card ? (card.sub ?? "") : "This atlas will not read ahead for you."}
          </div>
          {card?.figure && (
            <div style={{ fontFamily: "Pirata One", fontSize: 54, color: INK.gold, marginTop: 22 }}>
              {card.figure}
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end",
                      marginTop: "auto", paddingTop: 40, borderTop: `1px solid ${INK.rope}` }}>
          <div style={{ fontFamily: "Pirata One", fontSize: 30, color: INK.gold }}>
            {BRAND.name}
          </div>
          <div style={{ fontFamily: "IM Fell English", fontSize: 22, color: INK.muted2 }}>
            {ctx.chapterSet ? `as of chapter ${ctx.chapter}` : BRAND.prompt}
          </div>
        </div>
      </div>
    ),
    {
      width: W,
      height: H,
      fonts: await ogFonts(),
      headers: {
        // canon.json is a committed artifact; the key is family+slug+ch. Nothing
        // behind this URL can change without a deploy.
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    },
  );
}
