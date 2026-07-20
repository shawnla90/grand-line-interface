#!/usr/bin/env python3
"""Browser proof for the 90-second Grand Line trailer treatment."""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("AUDIT_URL", "http://localhost:3000")
RATE = float(os.environ.get("AUDIT_RATE", "2"))

EXPECTED_SHOTS = [
    "roger-execution-prologue",
    "luffy-punches-alvida",
    "orange-town-luffy-vs-buggy",
    "syrup-village-luffy-vs-kuro",
    "baratie-zoro-vs-mihawk",
    "nami-asks-for-help",
    "arlong-park-final-clash",
    "reverse-mountain",
    "arabasta-luffy-vs-crocodile-final",
    "jaya-approach",
    "knock-up-stream",
    "skypiea-luffy-vs-enel",
    "enies-lobby-luffy-vs-rob-lucci",
    "sabaody-luffy-punches-charloss",
    "marineford",
    "fishman-descent",
    "punk-hazard",
    "dressrosa",
    "zou",
    "whole-cake",
    "wano-approach",
    "onigashima-flight",
    "onigashima-landing",
    "egghead",
    "elbaph",
    "horizon",
]

EXPECTED_SCENES = {
    "sim-roger-execution-prologue",
    "sim-luffy-punches-alvida",
    "sim-orange-town-luffy-vs-buggy",
    "sim-syrup-village-luffy-vs-kuro",
    "sim-baratie-zoro-vs-mihawk",
    "sim-nami-asks-for-help",
    "sim-arlong-park-final-clash",
    "sim-arabasta-luffy-vs-crocodile-final",
    "sim-skypiea-luffy-vs-enel",
    "sim-enies-lobby-luffy-vs-rob-lucci",
    "sim-sabaody-luffy-punches-charloss",
}


def main() -> int:
    failures: list[str] = []
    checks = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal checks
        checks += 1
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        requests: list[str] = []
        page.on("console", lambda message: errors.append(message.text[:300]) if message.type == "error" else None)
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
        scene_times: dict[str, float] = {}
        started = time.time()
        timeout_s = 90 / RATE + 12
        while time.time() - started < timeout_s:
            state = page.evaluate(
                """() => {
                  const glyph = document.querySelector('.shipMarker > div > div:nth-child(2)');
                  const ship = document.querySelector('.shipMarker');
                  const sims = Object.fromEntries(Object.entries(window.__simScenes || {}).map(([id, value]) => [id, value.timeMs]));
                  return {
                    running: !!document.querySelector("button[aria-label='Stop journey']"),
                    elapsed: window.__journeyElapsedExact || 0,
                    shot: window.__journeyShotId || '',
                    projection: window.__map.getProjection().type,
                    center: [window.__map.getCenter().lng, window.__map.getCenter().lat],
                    pitch: window.__map.getPitch(),
                    zoom: window.__map.getZoom(),
                    reverseMountain: !!window.__map.getLayer('glb-reverse-mountain-twin-cape-voyage'),
                    marineford: !!window.__map.getLayer('glb-world-government-tarai-system'),
                    fishman: !!window.__map.getLayer('glb-fish-man-red-line-descent'),
                    punk: !!window.__map.getLayer('glb-punk-hazard-geographic-system'),
                    dressrosa: !!window.__map.getLayer('glb-dressrosa-green-bit'),
                    zou: !!window.__map.getLayer('glb-zou-zunesha'),
                    wholeCake: !!window.__map.getLayer('glb-totto-land-food-geography'),
                    wano: !!window.__map.getLayer('glb-wano-onigashima-country-system'),
                    egghead: !!window.__map.getLayer('glb-egghead-future-island-system'),
                    elbaph: !!window.__map.getLayer('glb-elbaph-adam-world-system'),
                    knockup: !!window.__map.getLayer('knockup-glb') || !!window.__map.getLayer('knockup3d'),
                    wanoAnim: window.__glbAnimationState?.['glb-wano-onigashima-country-system'] || null,
                    sims,
                    shipDisplay: ship ? getComputedStyle(ship).display : 'missing',
                    shipTransform: glyph?.style.transform || '',
                    videoCount: document.querySelectorAll('video[src*="op1188.mp4"]').length,
                  };
                }"""
            )
            samples.append(state)
            for scene_id, scene_time in state["sims"].items():
                if scene_time is not None:
                    scene_times[scene_id] = max(scene_times.get(scene_id, 0), scene_time)
            if not state["running"] and state["elapsed"] >= 89_900:
                break
            page.wait_for_timeout(100)

        shot_ids = [shot["id"] for shot in treatment["shots"]]
        check("treatment remains exactly 90 seconds", treatment["durationMs"] == 90_000)
        check("all trailer shots are scheduled in order", shot_ids == EXPECTED_SHOTS, str(shot_ids))
        check("Punk Hazard owns a five-second shot", any(s["id"] == "punk-hazard" and s["toMs"] - s["fromMs"] == 5_000 for s in treatment["shots"]))
        check("Journey stays in Mercator", all(s["projection"] == "mercator" for s in samples[3:]))

        seen_scenes = set(scene_times)
        check("all eleven selected simulations render", EXPECTED_SCENES <= seen_scenes, str(sorted(EXPECTED_SCENES - seen_scenes)))
        progressed = {scene for scene, max_time in scene_times.items() if max_time >= 4_500}
        check("the scene edit advances action instead of holding opening frames", len(EXPECTED_SCENES & progressed) >= 9, str(sorted(EXPECTED_SCENES - progressed)))

        ascent = [s for s in samples if s["shot"] == "knock-up-stream"]
        check("Skypiea receives the full five-second authored slot", bool(ascent) and max(s["elapsed"] for s in ascent) - min(s["elapsed"] for s in ascent) >= 4_500)
        check("Knock-Up Stream renders during the ascent", any(s["knockup"] for s in ascent))
        check("Skypiea camera climbs steeply", bool(ascent) and max(s["pitch"] for s in ascent) >= 58)

        punk = [s for s in samples if s["shot"] == "punk-hazard"]
        check("Punk Hazard loads and fills a close shot", any(s["punk"] and s["zoom"] >= 6.5 for s in punk), f"samples={len(punk)}, maxZoom={max((s['zoom'] for s in punk), default=0):.2f}")
        check("Punk Hazard GLB is actually requested", any("punk-hazard-geographic-system.glb" in url for url in requests))

        for shot_id, key, label in [
            ("reverse-mountain", "reverseMountain", "Reverse Mountain"),
            ("marineford", "marineford", "Marineford"),
            ("fishman-descent", "fishman", "Fish-Man descent"),
            ("dressrosa", "dressrosa", "Dressrosa"),
            ("zou", "zou", "Zou"),
            ("whole-cake", "wholeCake", "Whole Cake"),
            ("egghead", "egghead", "Egghead"),
            ("elbaph", "elbaph", "Elbaph"),
        ]:
            check(f"{label} renders in its own shot", any(s["shot"] == shot_id and s[key] for s in samples))

        onigashima = [s for s in samples if s["shot"] == "onigashima-flight"]
        check("Wano model renders during Onigashima flight", any(s["wano"] for s in onigashima))
        check("Onigashima is framed large", any(s["zoom"] >= 7.1 for s in onigashima), f"maxZoom={max((s['zoom'] for s in onigashima), default=0):.2f}")
        check("camera holds the complete Wano model in frame", any(abs(s["center"][0] - 118.2306) < 0.2 and abs(s["center"][1] - 7.5751) < 0.2 for s in onigashima))
        animated = [s for s in onigashima if s["wanoAnim"]]
        check("real geographic-shift animation owns the lift", any("onigashima_geographic_shift" in s["wanoAnim"]["clips"] for s in animated))
        check("chart-marker Sunny is hidden during Wano flight", bool(onigashima) and all(s["shipDisplay"] == "none" for s in onigashima[2:]))
        check("no fake vertical ship transform remains", not any("translateY" in s["shipTransform"] for s in samples))

        check("1188 vertical video is absent from Journey", not any(s["videoCount"] for s in samples) and not any("op1188.mp4" in url for url in requests))
        check("Journey completes on its own", bool(samples) and not samples[-1]["running"] and samples[-1]["elapsed"] >= 89_900)
        check("zero console or page errors", not errors, str(errors[:5]))
        browser.close()

    print(f"\n{checks - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
