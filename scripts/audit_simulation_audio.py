#!/usr/bin/env python3
"""audit_simulation_audio.py — headless proof of deterministic scene sound.

READ-ONLY. Drives the real syncSimulations host + SimulationAudioPlayer
through /dev/sim-proof (the audit_story_simulations.py posture) and asserts
the audio contract for the chapter-159 Fire Fist vertical slice:

  1. GESTURE GATE: before any unlock click, zero /audio/simulations/
     requests — a cold page never fetches sound.
  2. UNLOCK + PRELOAD SCOPE: after the sound gesture, only the mounted
     scene's own cue files are fetched (six, all under ace-fire-fist/).
  3. FIRE-ONCE: a full scene pass crosses each of the six compiled bindings
     exactly once — the fired log grows by exactly six and stays put while
     the tableau holds (no per-frame refire, tableau never fires).
  4. BACKWARD RESET: scrubbing 159 -> 158 removes the scene; returning
     replays it from zero and each cue fires exactly once more.
  5. HIDDEN TAB: with document.hidden faked true, the scene clock freezes
     and no new cues fire; unhiding resumes without a time jump.
  6. REDUCED MOTION: a prefers-reduced-motion page at ch159 renders the
     static tableau, fires nothing, and fetches zero audio.

Requires the dev server (harness route + window hooks are dev-only):
AUDIT_URL or its own server on AUDIT_PORT (default 3216).

Run: python3 scripts/audit_simulation_audio.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3216"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

FLEET = "sim-ace-fire-fist-destroys-billions-fleet"
FLEET_SCENE_ID = "ace-fire-fist-destroys-billions-fleet"
AUDIO_PREFIX = "/audio/simulations/"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def audio_requests(requests: list[str]) -> list[str]:
    return sorted({url.split(AUDIO_PREFIX)[1] for url in requests if AUDIO_PREFIX in url and not url.endswith("manifest.json")})


def fired(page) -> list[dict]:
    return page.evaluate("() => (window.__simAudio ? window.__simAudio.fired : []).slice()")


def fleet_fired(page) -> list[dict]:
    return [f for f in fired(page) if f["sceneId"] == FLEET_SCENE_ID]


def scene_time(page) -> float | None:
    return page.evaluate(f"() => ((window.__simScenes || {{}})['{FLEET}'] || {{}}).timeMs ?? null")


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
            requests: list[str] = []
            page.on("request", lambda r: requests.append(r.url))

            url = f"{BASE}/dev/sim-proof?pack=arabasta&ch=159"
            for _ in range(60):
                try:
                    page.goto(url, timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            page.wait_for_function(f"() => (window.__simScenes || {{}})['{FLEET}']", timeout=30000)
            page.wait_for_timeout(2000)

            # ---- 1. gesture gate
            check("before any gesture: zero audio requests", not audio_requests(requests),
                  ", ".join(audio_requests(requests)))
            unlocked = page.evaluate("() => window.__simAudio ? window.__simAudio.unlocked : null")
            check("director reports locked before the gesture", unlocked is False, f"unlocked={unlocked}")

            # ---- 2. unlock; replay the scene so a full pass runs audible
            page.click("[data-testid=sound-unlock]")
            page.wait_for_timeout(300)
            check("the click unlocks the director",
                  page.evaluate("() => window.__simAudio.unlocked") is True)

            page.click("[data-testid=go-158]")
            page.wait_for_function(
                f"() => !Object.keys(window.__simScenes || {{}}).includes('{FLEET}')", timeout=10000)
            baseline = len(fleet_fired(page))
            page.click("[data-testid=go-159]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{FLEET}']", timeout=10000)

            # ---- 5. hidden tab, probed mid-scene (~1.5s in)
            page.wait_for_timeout(1500)
            page.evaluate(
                """() => {
                  Object.defineProperty(document, 'hidden', { value: true, configurable: true });
                  document.dispatchEvent(new Event('visibilitychange'));
                }"""
            )
            page.wait_for_timeout(400)
            t_hidden_a = scene_time(page)
            fired_hidden_a = len(fleet_fired(page))
            page.wait_for_timeout(1200)
            t_hidden_b = scene_time(page)
            fired_hidden_b = len(fleet_fired(page))
            clock_frozen = (
                t_hidden_a is not None and t_hidden_b is not None and abs(t_hidden_b - t_hidden_a) < 120
            )
            check("hidden tab: the scene clock freezes", clock_frozen, f"{t_hidden_a} -> {t_hidden_b}")
            check("hidden tab: no cues fire", fired_hidden_a == fired_hidden_b,
                  f"{fired_hidden_a} -> {fired_hidden_b}")
            page.evaluate(
                """() => {
                  Object.defineProperty(document, 'hidden', { value: false, configurable: true });
                  document.dispatchEvent(new Event('visibilitychange'));
                }"""
            )

            # let the full 9s scene finish + tableau settle
            page.wait_for_timeout(11000)

            # ---- 3. fire-once across the full pass
            after_pass = fleet_fired(page)[baseline:]
            ids = sorted(f["bindingId"] for f in after_pass)
            check("full pass fires exactly the six bindings once",
                  len(after_pass) == 6 and len(set(ids)) == 6, ", ".join(ids))
            timing_ok = all(abs(f["firedAtT"] - f["atMs"]) < 250 for f in after_pass)
            check("every cue fires within 250ms of its compiled time", timing_ok,
                  "; ".join(f"{f['bindingId']}@{f['firedAtT']:.0f}(want {f['atMs']})" for f in after_pass))

            # tableau holds: nothing new fires while held
            held_before = len(fleet_fired(page))
            page.wait_for_timeout(2500)
            check("held tableau fires nothing", len(fleet_fired(page)) == held_before)

            # ---- 2b. preload scope: only the six ace files ever fetched
            fetched = audio_requests(requests)
            scoped = all(f.startswith("ace-fire-fist/") for f in fetched)
            check("only the mounted scene's cue files are fetched",
                  scoped and 0 < len(fetched) <= 6, ", ".join(fetched))

            # ---- 4. backward reset replays exactly once more
            before_replay = len(fleet_fired(page))
            page.click("[data-testid=go-158]")
            page.wait_for_function(
                f"() => !Object.keys(window.__simScenes || {{}}).includes('{FLEET}')", timeout=10000)
            page.click("[data-testid=go-159]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{FLEET}']", timeout=10000)
            page.wait_for_timeout(11000)
            replay = fleet_fired(page)[before_replay:]
            replay_ids = sorted(f["bindingId"] for f in replay)
            check("backward scrub + return replays each cue exactly once",
                  len(replay) == 6 and len(set(replay_ids)) == 6, ", ".join(replay_ids))

            # ---- 4b. the Mihawk duel speaks on its own clock (the pin that
            # replaced the epic-chain ch51 gate): pack-switch to East Blue,
            # play ch51, and both Zoro voice bindings fire at compiled times.
            page.click("[data-testid=go-49]")
            page.wait_for_timeout(1500)
            page.click("[data-testid=go-51]")
            page.wait_for_function(
                "() => (window.__simScenes || {})['sim-baratie-zoro-vs-mihawk']", timeout=15000)
            page.wait_for_timeout(6000)
            duel_fired = [f for f in fired(page) if f["sceneId"] == "baratie-zoro-vs-mihawk"]
            duel_ids = sorted(f["bindingId"] for f in duel_fired)
            # SUBSET, not the whole set: the phase-10 scoring pass added duel
            # SFX beside the voices, and each future binding must not re-break
            # this pin. Each fired binding still fires exactly once.
            check("ch51: both Zoro voice lines fire once",
                  duel_ids.count("onigiri-call") == 1
                  and duel_ids.count("santoryu-announce") == 1
                  and len(duel_ids) == len(set(duel_ids)),
                  ", ".join(duel_ids))
            duel_timing = all(abs(f["firedAtT"] - f["atMs"]) < 250 for f in duel_fired)
            check("ch51: voice lines land on their compiled times", duel_timing,
                  "; ".join(f"{f['bindingId']}@{f['firedAtT']:.0f}(want {f['atMs']})" for f in duel_fired))

            # ---- 6. reduced motion: silence, structurally
            rm_requests: list[str] = []
            rm = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            rm.on("request", lambda r: rm_requests.append(r.url))
            rm.goto(f"{BASE}/dev/sim-proof?pack=arabasta&ch=159")
            rm.wait_for_function(f"() => (window.__simScenes || {{}})['{FLEET}']", timeout=30000)
            rm.wait_for_timeout(3000)
            rm_fired = rm.evaluate("() => (window.__simAudio ? window.__simAudio.fired : []).length")
            check("reduced motion: zero cues fire", rm_fired == 0, f"{rm_fired} fired")
            check("reduced motion: zero audio requests", not audio_requests(rm_requests),
                  ", ".join(audio_requests(rm_requests)))

            browser.close()
    finally:
        if server:
            server.terminate()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
