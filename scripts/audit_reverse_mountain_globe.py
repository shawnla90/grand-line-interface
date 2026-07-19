#!/usr/bin/env python3
"""Photograph and pixel-prove the Reverse Mountain GLB on MapLibre globe."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "review" / "glb"
BASE = os.environ.get("AUDIT_URL", "http://localhost:3215")
ASSET = "reverse-mountain-twin-cape-voyage"
LAYER = f"glb-{ASSET}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with_model = OUT / f"{ASSET}--globe.png"
    without_model = OUT / f"{ASSET}--globe-without.png"
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 820})
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(f"{BASE}/?ch=101", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=60000)
        page.locator("button[title='Camera follows the ship (F)']").click()
        page.evaluate("() => window.__map.jumpTo({center:[-179,-2], zoom:6.4, pitch:55, bearing:0})")
        page.wait_for_function("([id]) => !!window.__glbScenes?.[id]", arg=[LAYER], timeout=60000)
        page.wait_for_timeout(1800)
        projection = page.evaluate("() => window.__map.getProjection().type")
        present = page.evaluate("([id]) => !!window.__map.getLayer(id)", [LAYER])
        canvas = page.locator("canvas").first
        canvas.screenshot(path=str(with_model))
        page.evaluate("([id]) => window.__map.removeLayer(id)", [LAYER])
        page.wait_for_timeout(700)
        canvas.screenshot(path=str(without_model))
        browser.close()

    before = Image.open(with_model).convert("RGB")
    after = Image.open(without_model).convert("RGB")
    diff = ImageChops.difference(before, after)
    raw = diff.tobytes()
    changed = sum(1 for offset in range(0, len(raw), 3) if raw[offset] or raw[offset + 1] or raw[offset + 2])
    ratio = changed / (before.width * before.height)

    checks = [
        ("projection remains globe", projection == "globe", projection),
        ("Reverse Mountain layer is present", present, str(present)),
        ("model changes the globe pixels", ratio >= 0.01, f"{ratio:.2%} pixels changed"),
        ("zero browser errors", not errors, str(errors[:3])),
    ]
    failed = 0
    for name, ok, detail in checks:
        print(f"  [{'ok ' if ok else 'FAIL'}] {name} — {detail}")
        failed += int(not ok)
    print(f"\nproof: {with_model.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
