#!/usr/bin/env python3
"""audit_terrain.py — Landfall contact sheets + spoiler shots.

READ-ONLY. For each hero island, screenshots the dive at z5 and z8 with the
story read past its debut (ch 1050), plus the SAME camera at ch 1 (must be
bare ocean). Writes everything into data/review/terrain/ with an index.html
contact sheet for the human checkpoint — the Water-7-checkpoint ritual:
eyeball before mass-styling more heroes.

The hard pixel assertions (fogged geometry contributes zero pixels) live in
audit_geo.py; this script is the eyeball surface.

Run: AUDIT_URL=http://localhost:3000 python3 scripts/audit_terrain.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "review" / "terrain"
PORT = int(os.environ.get("AUDIT_PORT", "3212"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

HEROES = {
    "punk-hazard": (18.7, -5.2),
    "arabasta-kingdom": (-125.5, -2.1),
    "skypiea": (-91.1, 17.1),
}
SHOTS = [("z5", 5.0), ("z8", 8.0)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    server = None
    if "AUDIT_URL" not in os.environ:
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    cells = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=1050", timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            def shoot(ch: int, slug: str, lng: float, lat: float, zoom: float, name: str):
                page.goto(f"{BASE}/?ch={ch}")
                page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=30000)
                page.wait_for_timeout(400)
                page.evaluate(f"() => window.__map.jumpTo({{center: [{lng}, {lat}], zoom: {zoom}}})")
                page.wait_for_function("() => window.__map.loaded()", timeout=15000)
                page.wait_for_timeout(600)
                path = OUT / name
                page.screenshot(path=str(path))
                return name

            for slug, (lng, lat) in HEROES.items():
                row = [f"<h2>{slug}</h2><div class='row'>"]
                for zname, z in SHOTS:
                    f = shoot(1050, slug, lng, lat, z, f"{slug}_{zname}_ch1050.png")
                    row.append(f"<figure><img src='{f}'><figcaption>ch 1050 · {zname}</figcaption></figure>")
                f = shoot(1, slug, lng, lat, 5.0, f"{slug}_z5_ch1.png")
                row.append(f"<figure><img src='{f}'><figcaption>ch 1 · z5 — MUST be bare ocean</figcaption></figure>")
                row.append("</div>")
                cells.append("".join(row))
                print(f"  {slug}: 3 shots")
            browser.close()
    finally:
        if server:
            server.terminate()

    (OUT / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Landfall terrain — review</title>"
        "<style>body{background:#0b1120;color:#e2e8f0;font:14px system-ui;margin:24px}"
        "h2{margin:28px 0 8px;font-size:16px}.row{display:flex;gap:10px;flex-wrap:wrap}"
        "figure{margin:0}img{width:440px;border-radius:8px;border:1px solid #1e293b}"
        "figcaption{font-size:11px;color:#94a3b8;margin-top:4px}</style>"
        "<h1>Landfall terrain — hero island contact sheet</h1>"
        "<p>Checkpoint ritual: eyeball each dive before mass-styling more heroes. "
        "The ch 1 column proves the fog holds.</p>"
        + "".join(cells)
    )
    print(f"\ncontact sheet: {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
