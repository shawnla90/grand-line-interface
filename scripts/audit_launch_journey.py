#!/usr/bin/env python3
"""Accelerated browser proof for the one launch Journey treatment."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("AUDIT_URL", "http://localhost:3000")
RATE = float(os.environ.get("AUDIT_RATE", "3"))


def main() -> int:
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        requests: list[str] = []
        page.on("console", lambda message: errors.append(message.text[:240]) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"PAGEERROR {error}"))
        page.on("request", lambda request: requests.append(request.url))
        page.goto(f"{BASE}/?ch=1", wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=60_000)
        page.evaluate(f"window.__journeyRate = {RATE}")
        page.click("button[aria-label='Play cinematic journey']")
        page.wait_for_selector("button[aria-label='Stop journey']", timeout=5_000)
        page.wait_for_function("() => window.__journeyTreatment", timeout=5_000)

        treatment = page.evaluate("() => window.__journeyTreatment")
        samples: list[dict] = []
        started = time.time()
        while time.time() - started < 45:
            state = page.evaluate(
                """() => {
                  const glyph = document.querySelector('.shipMarker > div > div:nth-child(2)');
                  const video = document.querySelector('video[src*="op1188.mp4"]');
                  const caption = document.querySelector('.pointer-events-none .rounded-2xl div');
                  return {
                    running: !!document.querySelector("button[aria-label='Stop journey']"),
                    chapter: +((document.querySelector("input[aria-label='Chapter']") || {}).value || 1),
                    caption: caption?.textContent || '',
                    projection: window.__map.getProjection().type,
                    lat: window.__map.getCenter().lat,
                    pitch: window.__map.getPitch(),
                    zoom: window.__map.getZoom(),
                    wano: !!window.__map.getLayer('glb-wano-onigashima-country-system'),
                    egghead: !!window.__map.getLayer('glb-egghead-future-island-system'),
                    elbaph: !!window.__map.getLayer('glb-elbaph-adam-world-system'),
                    punk: !!window.__map.getLayer('glb-punk-hazard-geographic-system'),
                    knockup: !!window.__map.getLayer('knockup-glb') || !!window.__map.getLayer('knockup3d'),
                    sims: Object.keys(window.__simScenes || {}),
                    wanoAnim: window.__glbAnimationState?.['glb-wano-onigashima-country-system'] || null,
                    shipTransform: glyph?.style.transform || '',
                    videoVisible: !!video && +getComputedStyle(video.closest('[aria-hidden]')).opacity > .5,
                    videoTime: video?.currentTime || 0,
                  };
                }"""
            )
            state["wall"] = time.time() - started
            samples.append(state)
            if not state["running"] and state["wall"] > 2:
                break
            page.wait_for_timeout(100)

        check("treatment is exactly 90 seconds", treatment["durationMs"] == 90_000, str(treatment["durationMs"]))
        opening = [sample for sample in samples if sample["wall"] * RATE <= 5.2]
        opening_max = max((sample["chapter"] for sample in opening), default=1)
        check("opening leaves chapter one immediately", opening_max >= 40, f"chapter 1 -> {opening_max}")
        seen_sims = {scene for sample in samples for scene in sample["sims"]}
        early_sims = {
            "sim-roger-execution-prologue",
            "sim-baratie-zoro-vs-mihawk",
            "sim-arlong-park-final-clash",
        }
        check("Roger, Mihawk, and Arlong scenes populate their authored cuts", early_sims <= seen_sims, str(sorted(early_sims - seen_sims)))
        check("Journey forces the close-up Mercator projection", all(sample["projection"] == "mercator" for sample in samples[3:]), str({s['projection'] for s in samples}))

        ascent = [sample for sample in samples if 235 <= sample["chapter"] <= 237]
        ascent_time = (ascent[-1]["wall"] - ascent[0]["wall"]) * RATE if len(ascent) > 1 else 0
        ascent_lat = max((sample["lat"] for sample in ascent), default=0) - min((sample["lat"] for sample in ascent), default=0)
        check("Skypiea receives its authored five-second climb", ascent_time >= 4.2, f"{ascent_time:.1f}s")
        check("Skypiea camera climbs with pitch", bool(ascent) and max(s["pitch"] for s in ascent) >= 50 and ascent_lat >= 3, f"pitch {max((s['pitch'] for s in ascent), default=0):.1f}, dlat {ascent_lat:.1f}")
        check("Knock-Up Stream renders during the climb", any(sample["knockup"] for sample in ascent))

        check("Wano and Onigashima load in the Journey", any(sample["wano"] for sample in samples))
        animated = [sample for sample in samples if sample["wanoAnim"]]
        check("Onigashima geographic-shift animation is sampled", any("onigashima_geographic_shift" in sample["wanoAnim"]["clips"] for sample in animated), str([sample["wanoAnim"] for sample in animated[:2]]))
        lifted = [sample for sample in samples if "translateY(-" in sample["shipTransform"]]
        check("the ship rises with Onigashima", bool(lifted), lifted[-1]["shipTransform"] if lifted else "no lift transform")

        check("Egghead loads as a close 3D stage", any(sample["egghead"] for sample in samples))
        check("Elbaph loads as a close 3D stage", any(sample["elbaph"] for sample in samples))
        media = [sample for sample in samples if sample["videoVisible"]]
        check("the chapter 1188 master plays inside the final shot", bool(media) and max(s["videoTime"] for s in media) >= 9, f"{len(media)} samples, max {max((s['videoTime'] for s in media), default=0):.2f}s")

        punk_requests = [url for url in requests if "punk-hazard-geographic-system" in url]
        check("Punk Hazard is skipped, not loaded", not any(sample["punk"] for sample in samples) and not punk_requests, str(punk_requests))
        check("the Journey completes on its own", bool(samples) and not samples[-1]["running"], f"{samples[-1]['wall']:.1f}s wall at {RATE:g}x")
        check("chapter 1188 keeps a manual full-view entry point", page.locator("a[aria-label='Open the Chapter 1188 animated breakdown']").count() == 1)
        check("zero console or page errors", not errors, str(errors[:4]))
        browser.close()

    print(f"\n{17 - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
