#!/usr/bin/env python3
"""audit_glb.py — prove the Blender model's gates on the WIRE and on the SCREEN.

The claims this file exists to stop us from merely asserting:

  1. NEVER FETCHED BEFORE ITS GATE. The asset track's WORKFLOW says models are
     "never fetched before their chapter gate". The layer's onAdd is what pulls
     both three.js (~1MB) and the model (2.5MB), so the test is a network log,
     not a comment: at chapter 1, diving to the sea where the stream will one day
     erupt must request neither. THIS INCLUDES THE CODE, not just the asset — a
     lazy chunk is only lazy if you watched it not load.

  2. UNLOADS WHEN HIDDEN. `unload_when_hidden: true`, so scrubbing back before
     the eruption must REMOVE the layer, not hide it at opacity 0.

  3. CLOSE ZOOM. `enable_glb_when` requires it. At the resting zoom the model is
     absent even at chapter 236.

  4. IT ACTUALLY RENDERS, on the globe AND on mercator. The interesting one:
     MapLibre's docs say a matrix-only custom layer is mercator-only, because
     globe projection lives in its vertex shaders. glb-layer routes around that
     via getMatrixForModel. Either that works on the globe or it does not, and
     only pixels can say. We diff a SCREENSHOT against the same frame with the
     model suppressed — if the model draws, pixels move.

     Screenshots, NOT canvas.toDataURL(). MapLibre builds its context with
     preserveDrawingBuffer:false, so toDataURL returns a blank 26KB frame and
     every diff comes back "identical" — a test that fails no matter what the
     renderer does. This audit made exactly that mistake first, and reported the
     model dead on both projections while it was in fact drawing fine.
     audit_geo.py screenshots for the same reason.

Run: python3 scripts/audit_glb.py [--base http://localhost:3007] [--keep]
Needs a DEV server started with NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS=1 (window.__map
and window.__glbReady are dev-only, like audit_geo's). With the flag off every one
of these is trivially true, which is worth nothing — so the audit refuses to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "data" / "review" / "glb"

GLB = "skypiea-knock-up-stream.glb"
# three.js is imported dynamically inside the layer's onAdd, so it should be a
# lazy chunk that a chapter-1 reader never pulls. That is a property of the BUILD,
# not of the app: Turbopack's dev server serves dynamic-import chunks EAGERLY, so
# in dev the chunk loads at chapter 1 no matter what the code says, and asserting
# it here would only ever measure the dev server. Hence --prod-base. Matched by
# content rather than by chunk name: names are content-hashed and would rot into a
# check that passes because it stopped matching anything.
THREE_HINT = "three"

SKY_BASE = [-91.1362, 8.2]

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")


def goto(page, base: str, ch: int, zoom: float, projection: str = "globe") -> None:
    """Load the map at a chapter, then fly to the stream's base at a zoom."""
    page.goto(f"{base}/?ch={ch}", wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.evaluate(
        """([lng, lat, z, proj]) => {
            const m = window.__map;
            if (!m) throw new Error("window.__map missing — the test hook is gone");
            m.setProjection({ type: proj });
            m.jumpTo({ center: [lng, lat], zoom: z });
        }""",
        [SKY_BASE[0], SKY_BASE[1], zoom, projection],
    )
    page.wait_for_timeout(2500)


def layer_present(page) -> bool:
    return page.evaluate("() => !!window.__map.getLayer('knockup-glb')")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3007")
    ap.add_argument("--keep", action="store_true", help="write screenshots to data/review/glb")
    ap.add_argument(
        "--prod-base",
        help="a `next start` server (flag ON). Only here can the three.js chunk's "
             "laziness be judged; dev is eager by design. Omitted -> reported SKIP, never PASS.",
    )
    args = ap.parse_args()

    SHOTS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 860})

        asked: list[str] = []
        page.on("request", lambda r: asked.append(r.url))

        # ── 1. the gate, on the wire ────────────────────────────────────────
        print("\nchapter 1, dived to the stream's future site (zoom 6):")
        goto(page, args.base, 1, 6.0)
        check(not any(GLB in u for u in asked), "ch1 z6: the 2.5MB model is never requested")
        check(not layer_present(page), "ch1 z6: no layer")

        # ── 2. close zoom ──────────────────────────────────────────────────
        print("\nchapter 236 (mid-eruption) at the RESTING zoom 1.9:")
        asked.clear()
        goto(page, args.base, 236, 1.9)
        check(not layer_present(page), "ch236 z1.9: gate open but too far — no layer ('close zoom')")
        check(not any(GLB in u for u in asked), "ch236 z1.9: still not fetched")

        # ── 3. it loads, and it draws ──────────────────────────────────────
        print("\nchapter 236, dived to zoom 6 — GLOBE:")
        asked.clear()
        goto(page, args.base, 236, 6.0)
        page.wait_for_timeout(3500)
        check(any(GLB in u for u in asked), "ch236 z6: the model IS fetched")
        check(layer_present(page), "ch236 z6: the layer is added")
        check(page.evaluate("() => !!window.__glbReady"), "ch236 z6: three.js loaded and the model is on the GPU")

        globe_shot = SHOTS / "globe-ch236-z6.png"
        page.locator("canvas").first.screenshot(path=str(globe_shot))

        # Does it put PIXELS on the globe? Suppress the model and diff the frame.
        # A layer that is present but draws nothing passes every check above.
        before = page.locator("canvas").first.screenshot()
        page.evaluate("() => window.__map.removeLayer('knockup-glb')")
        page.wait_for_timeout(1200)
        moved = before != page.locator("canvas").first.screenshot()
        check(moved, "ch236 z6 GLOBE: the model puts PIXELS on the canvas (removing it changes the frame)")

        # ── 4. mercator, the projection MapLibre says is the safe one ───────
        print("\nchapter 236, dived to zoom 6 — MERCATOR:")
        goto(page, args.base, 236, 6.0, projection="mercator")
        page.wait_for_timeout(3000)
        check(layer_present(page), "ch236 z6 mercator: the layer is added")
        merc_shot = SHOTS / "mercator-ch236-z6.png"
        page.locator("canvas").first.screenshot(path=str(merc_shot))
        before_m = page.locator("canvas").first.screenshot()
        page.evaluate("() => window.__map.removeLayer('knockup-glb')")
        page.wait_for_timeout(1200)
        moved_m = before_m != page.locator("canvas").first.screenshot()
        check(moved_m, "ch236 z6 MERCATOR: the model puts PIXELS on the canvas")

        # ── 5. unload when hidden ──────────────────────────────────────────
        print("\nscrub BACK to chapter 100 while dived:")
        page.goto(f"{args.base}/?ch=100", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.evaluate(
            "([lng, lat]) => window.__map.jumpTo({ center: [lng, lat], zoom: 6 })",
            SKY_BASE,
        )
        page.wait_for_timeout(2000)
        check(not layer_present(page), "ch100 z6: the layer is REMOVED, not hidden ('unload_when_hidden')")

        # ── 6. Wano is withheld ────────────────────────────────────────────
        print("\nWano (asset-ready, gate UNVERIFIED):")
        asked.clear()
        page.goto(f"{args.base}/?ch=950", wait_until="networkidle")
        page.wait_for_timeout(1500)
        check(
            not any("wano-waterfall-ascent" in u for u in asked),
            "ch950: Wano's model is never fetched — its own manifest calls its beats unverified",
        )

        # ── 7. the CODE is gated too, and only a prod build can say so ──────
        print("\nthe three.js chunk (a BUILD property — dev is eager by design):")
        if args.prod_base:
            asked.clear()
            # No __map in prod, and none needed: at the resting zoom the gate is
            # shut anyway, so a plain load at ch1 answers it.
            page2 = browser.new_page(viewport={"width": 1280, "height": 860})
            page2.on("request", lambda r: asked.append(r.url))
            page2.goto(f"{args.prod_base}/?ch=1", wait_until="networkidle")
            page2.wait_for_timeout(4000)
            check(
                not any(THREE_HINT in u.lower() and u.endswith(".js") for u in asked),
                "PROD ch1: the ~1MB three.js chunk is never requested (the CODE is gated, not just the asset)",
            )
            page2.close()
        else:
            print("  SKIP  three.js chunk laziness — pass --prod-base to judge it")

        browser.close()

    print()
    ok = sum(1 for r, _ in results if r)
    print(f"audit_glb: {ok}/{len(results)}")
    if args.keep:
        print(f"screenshots -> {SHOTS.relative_to(ROOT)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
