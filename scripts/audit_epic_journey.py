#!/usr/bin/env python3
"""Accelerated browser proof for Epic audio, movement, scenes, and transits."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
import json

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3215"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")
RATE = float(os.environ.get("AUDIT_RATE", "10"))


def main() -> int:
    server = None
    failures: list[str] = []
    if "AUDIT_URL" not in os.environ:
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors: list[str] = []
            audio_requests: list[tuple[str, float]] = []
            glb_requests: list[str] = []
            page.on("console", lambda message: errors.append(message.text[:200]) if message.type == "error" else None)
            page.on("pageerror", lambda error: errors.append(f"PAGEERROR {error}"))
            page.on(
                "request",
                lambda request: audio_requests.append((request.url, time.time()))
                if "/audio/epic-journey/" in request.url and request.url.endswith(".mp3")
                else glb_requests.append(request.url)
                if "skypiea-knock-up-stream.glb" in request.url
                else None,
            )

            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=1", timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=60000)
            page.evaluate(f"window.__epicJourneyRate = {RATE}")
            page.click("button[aria-label='Play Epic Journey with audio']")
            page.wait_for_selector("button[aria-label='Stop Epic Journey']", timeout=5000)

            standard_disabled = page.locator("button[aria-label='Play cinematic journey']").is_disabled()
            captions: set[str] = set()
            samples: list[dict] = []
            t0 = time.time()
            while time.time() - t0 < 45:
                state = page.evaluate(
                    """() => ({
                      running: !!document.querySelector("button[aria-label='Stop Epic Journey']"),
                      caption: (document.querySelector('.pointer-events-none .rounded-2xl div') || {}).textContent || '',
                      cue: (document.querySelector('[aria-live="polite"] div:last-child') || {}).textContent || '',
                      chapter: +((document.querySelector("input[aria-label='Chapter']") || {}).value || 1),
                      centerLat: window.__map.getCenter().lat,
                      pitch: window.__map.getPitch(),
                      zoom: window.__map.getZoom(),
                      knockupGlb: !!window.__map.getLayer('knockup-glb'),
                      knockupRaster: !!window.__map.getLayer('knockup3d'),
                      mihawkScene: !!window.__map.getLayer('sim-baratie-zoro-vs-mihawk'),
                      mihawkTime: window.__simScenes?.['sim-baratie-zoro-vs-mihawk']?.timeMs ?? null,
                    })"""
                )
                state["wall"] = time.time() - t0
                captions.add(state["caption"])
                samples.append(state)
                if not state["running"] and time.time() - t0 > 2:
                    break
                page.wait_for_timeout(100)

            requested_names = {url.rsplit("/", 1)[-1] for url, _ in audio_requests}
            disabled = {"lets-battle.mp3", "one-piece-laugh.mp3", "wendys-mansion.mp3"}
            registry = json.loads((ROOT / "data/epic-audio-cues.json").read_text())
            expected_names = {
                cue["src"].rsplit("/", 1)[-1]
                for cue in registry["cues"]
                if cue.get("enabled", True)
            }
            check("Epic Journey starts from a user gesture", standard_disabled)
            check("the accelerated full run ends", not page.locator("button[aria-label='Stop Epic Journey']").count(), f"{time.time() - t0:.1f}s")
            chapters = [sample["chapter"] for sample in samples]
            check("chapter progression reaches the final sea", max(chapters) >= 1125, f"max chapter {max(chapters)}")
            check("captions advance across audio and travel beats", len(captions) >= 12, f"{len(captions)} captions")
            # Subset, not equality: the scene-clock voice bindings also fetch
            # from /audio/epic-journey/ (the shared frozen OP library), so the
            # run legitimately requests more than the Epic chain's own cues.
            check(
                "every active Epic cue is requested",
                expected_names <= requested_names,
                f"{len(requested_names)} files; missing {sorted(expected_names - requested_names)}",
            )
            check("unidentified cues never load", not requested_names.intersection(disabled), str(requested_names.intersection(disabled)))

            opening = [sample for sample in samples if sample["wall"] <= 6]
            opening_max = max((sample["chapter"] for sample in opening), default=1)
            opening_unique = len({sample["chapter"] for sample in opening})
            # The intent is "Epic does not park on the opening beat". Reaching
            # ch43+ proves motion; the distinct-state count is sampling-grain
            # sensitive (0.5s wall = ~5s Epic per sample at 10x) and tightened
            # spuriously when the travel budget grew with the moment roster.
            check(
                "the first Epic minute sails beyond the opening barrel beat",
                opening_max >= 43 and opening_unique >= 8,
                f"chapter 1→{opening_max} across {opening_unique} chapter states",
            )
            request_at = {url.rsplit("/", 1)[-1]: at for url, at in audio_requests}
            bed_at = request_at.get("luffy-pirate-king.mp3", float("inf"))
            # This used to time bed→Gomu on the Epic CHAIN; the Gomu clip now
            # fires from the Alvida scene's own clock (an independent system
            # the bed structurally cannot block — "sails beyond the opening
            # barrel beat" above proves the voyage moves under the bed). What
            # remains to pin: the opening bed actually enters at the start,
            # and the scene-clock voice world reaches the run at all.
            gomu_at = request_at.get("gomu-gomu-no.mp3", float("inf"))
            check(
                "the opening bed enters at the start and scene voice joins the run",
                (bed_at - t0) < 3 and gomu_at < float("inf"),
                f"bed at +{bed_at - t0:.2f}s; first scene voice at +{gomu_at - t0:.2f}s ({RATE:g}x)",
            )

            mihawk = [sample for sample in samples if sample["mihawkScene"]]
            # The Zoro clips left the Epic chain — character voice lives on the
            # scene clocks now. The duel must speak through window.__simAudio
            # (the epic ♫ click unlocks the director, so cues fire audibly).
            duel_voice = page.evaluate(
                """() => (window.__simAudio ? window.__simAudio.fired : [])
                  .filter((f) => f.sceneId === 'baratie-zoro-vs-mihawk')
                  .map((f) => f.bindingId)"""
            )
            check("the Mihawk duel speaks from its own scene clock", len(duel_voice) >= 1, str(duel_voice))
            check(
                "the chapter-51 Mihawk simulation mounts and advances",
                bool(mihawk) and max((sample["mihawkTime"] or 0) for sample in mihawk) >= 350,
                f"{len(mihawk)} samples; scene clock {max((sample['mihawkTime'] or 0) for sample in mihawk):.0f}ms" if mihawk else "not mounted",
            )

            ascent = [sample for sample in samples if 235 <= sample["chapter"] <= 237]
            ascent_span = (ascent[-1]["wall"] - ascent[0]["wall"]) * RATE if len(ascent) >= 2 else 0
            lat_span = (
                max(sample["centerLat"] for sample in ascent) - min(sample["centerLat"] for sample in ascent)
                if ascent else 0
            )
            max_pitch = max((sample["pitch"] for sample in ascent), default=0)
            check("Skypiea ascent receives authored screen time", ascent_span >= 5, f"{ascent_span:.1f}s Epic time")
            check("the camera and boat climb the Knock-Up Stream", lat_span >= 5 and max_pitch >= 50, f"Δlat {lat_span:.2f}°, pitch {max_pitch:.1f}°")
            check(
                "the enabled Knock-Up Stream transition renders",
                any(sample["knockupRaster"] for sample in ascent)
                and any(sample["knockupGlb"] for sample in ascent)
                and bool(glb_requests),
                f"raster={any(sample['knockupRaster'] for sample in ascent)} glb={any(sample['knockupGlb'] for sample in ascent)} requests={len(glb_requests)}",
            )
            check("zero console or page errors", not errors, str(errors[:3]))

            before_standard = len(audio_requests)
            page.click("button[aria-label='Play cinematic journey']")
            page.wait_for_timeout(1200)
            check("standard Journey remains independently playable", page.locator("button[aria-label='Stop journey']").count() == 1)
            check("standard Journey requests no audio", len(audio_requests) == before_standard)
            page.click("button[aria-label='Stop journey']")
            browser.close()
    finally:
        if server:
            server.terminate()

    total = 16
    print(f"\n{total - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
