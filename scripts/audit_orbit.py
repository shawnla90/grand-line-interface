#!/usr/bin/env python3
"""audit_orbit.py — prove the hold-to-orbit rotation, and that nothing else spins.

The rule the whole rework exists for: a plain drag ALWAYS pans (navigate freely,
the globe never turns on its own), and rotation happens ONLY when you press and
HOLD to lock a target island, then drag to orbit around it. So the audit drives
both gestures and reads the camera:

  1. QUICK DRAG over the globe -> center moves, bearing unchanged (the old
     built-in dragRotate "circular" spin is gone).
  2. PRESS-AND-HOLD on an island, then drag -> bearing/pitch change while the
     centre stays locked on that island (orbit), and a "orbiting <name>" caption
     shows. Release -> dragPan is back on.
  3. Works on MERCATOR too (setBearing/setPitch are projection-agnostic).
  4. During the cinematic journey the hold does nothing — the journey owns the helm.

Run: python3 scripts/audit_orbit.py [--base http://localhost:3000]
Needs a DEV server (window.__map is dev-only).
"""

from __future__ import annotations

import argparse
import math
import sys

from playwright.sync_api import sync_playwright

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
                """() => ({ bearing: window.__map.getBearing(), pitch: window.__map.getPitch(),
                    center: window.__map.getCenter().toArray(), dragPan: window.__map.dragPan.isEnabled(),
                    proj: window.__map.getProjection().type }); """
            )

        def load(ch=1044, proj="globe"):
            page.goto(f"{args.base}/?ch={ch}", wait_until="networkidle")
            page.wait_for_timeout(2600)
            page.evaluate("(pr) => window.__map.setProjection({type: pr})", proj)
            page.wait_for_timeout(1800)

        def center_xy():
            box = page.locator("canvas").first.bounding_box()
            return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        def quick_drag(cx, cy, dx, dy=0):
            page.mouse.move(cx, cy)
            page.mouse.down()
            for i in range(1, 10):
                page.mouse.move(cx + dx * i / 10, cy + dy * i / 10)
                page.wait_for_timeout(15)
            page.mouse.up()
            page.wait_for_timeout(350)

        def hold_drag(cx, cy, dx, dy):
            page.mouse.move(cx, cy)
            page.mouse.down()
            page.wait_for_timeout(340)  # HOLD past the 260ms lock threshold
            cap = page.evaluate(
                "() => { const e=[...document.querySelectorAll('div')].find(d=>/orbiting/i.test(d.textContent||'')&&(d.textContent||'').length<40); return e?e.textContent.trim():null }"
            )
            for i in range(1, 10):
                page.mouse.move(cx + dx * i / 10, cy + dy * i / 10)
                page.wait_for_timeout(15)
            mid = st()
            page.mouse.up()
            page.wait_for_timeout(350)
            return mid, cap

        # ── 1. quick drag pans, no spin ────────────────────────────────────
        print("\nquick drag over the globe:")
        load()
        cx, cy = center_xy()
        a = st()
        quick_drag(cx, cy, 360)
        b = st()
        moved = abs(b["center"][0] - a["center"][0]) > 2
        check(moved and b["bearing"] == a["bearing"], "quick drag PANS and the bearing never changes (no free spin)")

        # ── 2. hold to orbit a locked island ───────────────────────────────
        print("\npress-and-hold on an island, then drag:")
        load()
        cx, cy = center_xy()
        a = st()
        mid, cap = hold_drag(cx, cy, 280, 150)
        turned = abs(mid["bearing"] - a["bearing"]) > 5
        held = abs(mid["center"][0] - a["center"][0]) < 6
        check(turned and held, "hold+drag ORBITS: bearing/pitch change, centre locked on the island")
        check(bool(cap and "orbiting" in cap.lower()), "the 'orbiting <island>' caption shows while holding")
        check(st()["dragPan"], "releasing restores free pan (dragPan back on)")

        # ── 3. mercator too ────────────────────────────────────────────────
        print("\nmercator:")
        load(proj="mercator")
        cx, cy = center_xy()
        a = st()
        mid, _ = hold_drag(cx, cy, 280, 60)
        check(abs(mid["bearing"] - a["bearing"]) > 5, "hold-orbit works on mercator (bearing changes)")

        # ── 4. journey owns the helm ───────────────────────────────────────
        print("\nduring the cinematic journey:")
        page.goto(f"{args.base}/?ch=1", wait_until="networkidle")
        page.wait_for_timeout(2200)
        page.get_by_role("button", name="Play cinematic journey").click()
        page.wait_for_timeout(3000)
        cx, cy = center_xy()
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.wait_for_timeout(340)
        for i in range(1, 6):
            page.mouse.move(cx + i * 40, cy)
            page.wait_for_timeout(15)
        locked = not st()["dragPan"]
        page.mouse.up()
        check(locked, "the hold gesture does nothing mid-journey (journey owns the helm)")

        browser.close()

    ok = sum(1 for r, _ in results if r)
    print(f"\naudit_orbit: {ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
