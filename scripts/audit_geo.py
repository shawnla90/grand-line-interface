#!/usr/bin/env python3
"""audit_geo.py — headless runtime audit of the geometry spoiler contract.

READ-ONLY. The biome/terrain work paints island landmasses with per-biome
inks. The contract: a fogged island's geometry reaches the DATA plane (slug/
debut/biome properties ship for all islands — Phase 5's established boundary)
but never the PIXEL plane. Opacity-0 features defeat queryRenderedFeatures,
so these checks sample real screenshot pixels.

  1. silhouette features carry ONLY {slug, debut, hand_drawn, biome}.
  2. per hero island (punk-hazard, arabasta-kingdom, skypiea):
     - at ch 1, hiding the island geometry layers changes ZERO pixels — i.e.
       nothing on screen at the island's location is attributable to its
       (fogged) landmass. Immune to background geometry (lane boundaries,
       belt hatch, the equator stroke) that defeats ocean-patch comparison.
     - at ch 1050 the same camera shows painted land (reveal actually renders),
     - back at ch 1 the pixels match the first shot again (re-fog).

Requires the dev server (window.__map is dev-only): set AUDIT_URL or the
script starts its own on AUDIT_PORT (default 3211).

Run: AUDIT_URL=http://localhost:3000 python3 scripts/audit_geo.py
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3211"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

HEROES = {
    "punk-hazard": {"lng": 18.7, "lat": -5.2},
    "arabasta-kingdom": {"lng": -125.5, "lat": -2.1},
    "skypiea": {"lng": -91.1, "lat": 17.1},
    # Its PIN debuts at ch. 68 (Arlong names it in East Blue), but nobody sees
    # the place until 604 — so the terrain carries its own later gate, and the
    # fogged-at-ch1 check below is really a check that a name is not a
    # photograph. See gen_terrain.py:TERRAIN_SEEN.
    "fish-man-island": {"lng": -5.93, "lat": -2.85},
}
# every layer that draws island geometry; extend as terrain layers land
GEO_LAYERS = ["island-shapes", "island-shapes-coast",
              "terrain-fill", "terrain-line", "terrain-glow",
              "sky-shadow", "sky-column", "sky-jet",
              "dive-shimmer"]
ZOOM = 4.0
PATCH = 44  # half-side of the sampled square, px

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    mark = "ok " if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def wait_map(page) -> None:
    page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=30000)
    page.wait_for_timeout(400)


def patch_at(page, lng: float, lat: float) -> np.ndarray:
    """Screenshot pixels in a small square around a world coordinate."""
    page.evaluate(f"() => window.__map.jumpTo({{center: [{lng}, {lat}], zoom: {ZOOM}}})")
    page.wait_for_function("() => window.__map.loaded()", timeout=15000)
    page.wait_for_timeout(500)
    px = page.evaluate(f"() => window.__map.project([{lng}, {lat}])")
    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    x, y = round(px["x"]), round(px["y"])
    box = (max(0, x - PATCH), max(0, y - PATCH), x + PATCH, y + PATCH)
    return np.asarray(shot.crop(box), dtype=np.float64)


def diff(a: np.ndarray, b: np.ndarray) -> float:
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    return float(np.abs(a[:h, :w] - b[:h, :w]).mean())


def main() -> int:
    server = None
    if "AUDIT_URL" not in os.environ:
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=1", timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1
            wait_map(page)

            # ---- 1. property whitelist on the live source
            props = page.evaluate(
                """() => (window.__map.querySourceFeatures('silhouettes') || [])
                         .map(f => Object.keys(f.properties))"""
            )
            allowed = {"slug", "debut", "hand_drawn", "biome"}
            extra = sorted({k for keys in props for k in keys} - allowed)
            check("silhouette features carry only slug/debut/hand_drawn/biome",
                  not extra, ", ".join(extra))

            # ---- 2. per-hero pixel contract
            hide = "".join(
                f"window.__map.setLayoutProperty('{l}','visibility','none');" for l in GEO_LAYERS
            )
            show = "".join(
                f"window.__map.setLayoutProperty('{l}','visibility','visible');" for l in GEO_LAYERS
            )

            for slug, h in HEROES.items():
                fogged = patch_at(page, h["lng"], h["lat"])

                # hide the island geometry layers: at ch 1 that must change
                # NOTHING — any pixel delta is fogged geometry leaking
                page.evaluate(f"() => {{ {hide} }}")
                page.wait_for_timeout(400)
                bare = patch_at(page, h["lng"], h["lat"])
                page.evaluate(f"() => {{ {show} }}")
                page.wait_for_timeout(400)
                d = diff(fogged, bare)
                check(f"ch1/{slug}: fogged geometry contributes zero pixels", d < 0.5,
                      f"mean px diff {d:.2f}")

                page.goto(f"{BASE}/?ch=1050")
                wait_map(page)
                revealed = patch_at(page, h["lng"], h["lat"])
                d = diff(fogged, revealed)
                check(f"ch1050/{slug}: revealed land actually renders", d > 3.0,
                      f"mean px diff {d:.2f}")

                page.goto(f"{BASE}/?ch=1")
                wait_map(page)
                refog = patch_at(page, h["lng"], h["lat"])
                d = diff(fogged, refog)
                check(f"refog/{slug}: back at ch1 the pixels match", d < 2.0,
                      f"mean px diff {d:.2f}")

            # ---- A NAME IS NOT A PHOTOGRAPH.
            # Fish-Man Island's pin debuts at ch. 68 — Arlong says the name in
            # East Blue, five hundred chapters before anyone goes there. So the
            # PIN is correctly on the map at 100, and the terrain must NOT be:
            # a reader who has only heard the name should not be able to zoom in
            # and find the bubble dome, the coral, and the shape of a city.
            # Pixels, not queryRenderedFeatures: that call ignores paint opacity,
            # so an opacity-0 feature still comes back from it (which is the
            # whole reason the checks above sample screenshots). Hide the terrain
            # layers at ch. 100 and the picture must not change by one pixel.
            page.goto(f"{BASE}/?ch=100")
            wait_map(page)
            fmi = HEROES["fish-man-island"]
            hide_terrain = "".join(
                f"window.__map.setLayoutProperty('{l}','visibility','none');"
                for l in ("terrain-fill", "terrain-line", "terrain-glow")
            )
            show_terrain = "".join(
                f"window.__map.setLayoutProperty('{l}','visibility','visible');"
                for l in ("terrain-fill", "terrain-line", "terrain-glow")
            )
            before = patch_at(page, fmi["lng"], fmi["lat"])
            page.evaluate(f"() => {{ {hide_terrain} }}")
            page.wait_for_timeout(400)
            after = patch_at(page, fmi["lng"], fmi["lat"])
            page.evaluate(f"() => {{ {show_terrain} }}")
            d = diff(before, after)
            check("ch100/fish-man-island: the name is charted but the place is not", d < 0.5,
                  f"mean px diff {d:.2f}")

            browser.close()
    finally:
        if server:
            server.terminate()

    print(f"\n{PASS}/{PASS + FAIL} geo audit checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
