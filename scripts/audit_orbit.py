#!/usr/bin/env python3
"""audit_orbit.py — prove grab-and-spin does the right thing at both zooms.

The one rule that matters and is easy to break: a left-drag ORBITS a dived-into
model, and PANS everywhere else. If orbit mode leaks out to the zoomed-out world,
the map stops being a map. If it fails to engage on a model, the feature does not
exist. So the audit drives a real left-drag in both states and reads the camera.

Two bugs this locked in after they were found the hard way:
  - modelPresent() must NOT scan getStyle().layers — a custom (three.js) layer
    never appears there, only getLayer() sees it, so the scan always concluded
    "no model" and orbit never engaged.
  - the model layer must be added when its DATA lands, not only on the next camera
    move — a reader who finished diving before the async load returned would sit
    on an island with no model, and orbit would have nothing to engage on.

Run: python3 scripts/audit_orbit.py [--base http://localhost:3000]
Needs a DEV server with NEXT_PUBLIC_RUNTIME_3D_ASSETS=1 (window.__map is dev-only).
"""

from __future__ import annotations

import argparse
import sys

from playwright.sync_api import sync_playwright

# Whole Cake Island — a model that is present at ch 655, both projections.
TOTTO = [72.2778, -2.819]
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3000")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        def st():
            return page.evaluate(
                """() => { const m = window.__map; return {
                    bearing: m.getBearing(), pitch: m.getPitch(),
                    center: m.getCenter().toArray(), zoom: m.getZoom(),
                    dragPan: m.dragPan.isEnabled(),
                    model: !!m.getLayer('glb-totto-land'),
                }; }"""
            )

        def drag(x0, y0, dx, dy):
            box = page.locator("canvas").first.bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            page.mouse.move(cx + x0, cy + y0)
            page.mouse.down()
            for i in range(1, 11):
                page.mouse.move(cx + x0 + dx * i / 10, cy + y0 + dy * i / 10)
                page.wait_for_timeout(20)
            page.mouse.up()
            page.wait_for_timeout(400)

        def dive(proj):
            page.goto(f"{args.base}/?ch=655", wait_until="networkidle")
            page.wait_for_timeout(2000)
            page.evaluate(
                "([c, proj]) => { window.__map.setProjection({type: proj}); "
                "window.__map.jumpTo({center: c, zoom: 6.2, pitch: 40, bearing: 0}); }",
                [TOTTO, proj],
            )
            page.wait_for_timeout(9000)  # the model loads async; orbit engages on idle

        for proj in ("globe", "mercator"):
            print(f"\ndived into Whole Cake — {proj.upper()}:")
            dive(proj)
            s0 = st()
            check(s0["model"], f"{proj}: the model layer is present after diving")
            check(not s0["dragPan"], f"{proj}: orbit engaged (dragPan is OFF)")

            b0 = st()
            drag(-250, 0, 500, 0)  # horizontal left-drag
            b1 = st()
            moved_bearing = abs(b1["bearing"] - b0["bearing"]) > 5
            held_center = abs(b1["center"][0] - b0["center"][0]) + abs(b1["center"][1] - b0["center"][1]) < 0.5
            check(moved_bearing and held_center,
                  f"{proj}: horizontal drag ORBITS (bearing moved, center held)")

            p0 = st()
            drag(0, -150, 0, 240)  # vertical drag
            p1 = st()
            check(abs(p1["pitch"] - p0["pitch"]) > 3, f"{proj}: vertical drag TILTS (pitch changed)")

        print("\n'level view' resets the camera:")
        page.evaluate("() => window.__map.jumpTo({center: [72.2778,-2.819], zoom: 6.2, pitch: 60, bearing: 120})")
        page.wait_for_timeout(3000)
        page.get_by_text("level view").first.click()
        page.wait_for_timeout(900)
        s = st()
        check(abs(s["pitch"]) < 2 and abs(((s["bearing"] + 180) % 360) - 180) < 2,
              "level view returns pitch and bearing to 0")

        print("\nzoomed OUT over open sea:")
        page.evaluate("() => window.__map.jumpTo({center: [0, 6], zoom: 2.5, pitch: 0, bearing: 0})")
        page.wait_for_timeout(3000)
        c0 = st()
        check(c0["dragPan"], "orbit released (dragPan is back ON)")
        drag(0, 0, 360, 0)
        c1 = st()
        check(abs(c1["center"][0] - c0["center"][0]) > 1, "left-drag PANS the world again")

        browser.close()

    ok = sum(1 for r, _ in results if r)
    print(f"\naudit_orbit: {ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
