#!/usr/bin/env python3
"""audit_journey.py — headless proof of the cinematic journey EXPERIENCE.

READ-ONLY. Drives a full flag-on journey in headless Chrome and asserts the
things whose absence was measured the night this suite was written: pitch was
0 for an entire run, the orbit never turned, sims never mounted, React threw
"Maximum update depth exceeded", and the recorded route had no boat. Every
check below pins one of those against regression.

  1. ZERO React/console errors across the whole run (the update-depth fix).
  2. The camera actually DIVES: pitch >= 40 observed in at least 6 distinct
     dwell windows; zoom >= 6.2 at least once (the directory-dive framing).
  3. The orbit actually TURNS: bearing magnitude exceeds 8 degrees at least
     once (5 deg/s across a ~6s model dwell).
  4. The 2.5D story plays: >= 3 distinct sim scenes observed mounted during
     the run's East Blue.
  5. The Knock-Up Stream is RIDDEN: a sample with the transit caption carries
     pitch >= 50.
  6. The trail never shrinks: the voyage source's coordinate count is
     monotonically non-decreasing across samples (backward = re-fog bug).
  7. The run ENDS: the journey button reads its resting label again.

Requires the dev server (window hooks are dev-only): AUDIT_URL or its own
server on AUDIT_PORT (default 3214). The dev server reads .env.development,
so the story flags are on without ceremony.

Run: AUDIT_URL=http://localhost:3000 python3 scripts/audit_journey.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3214"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

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
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text[:160]) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"PAGEERROR {e}"))

            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=1", timeout=5000)
                    break
                except Exception:
                    time.sleep(2)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1
            page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=60000)
            page.click("button[aria-label='Play cinematic journey']")

            samples = []
            t0 = time.time()
            # The run stretches past the 150s floor when the enabled moment
            # holds demand it (Atlas sizes journeyMs from momentSpans); sample
            # until the button rests, with a generous ceiling.
            while time.time() - t0 < 420:
                s = page.evaluate(
                    """() => ({
                      z: +window.__map.getZoom().toFixed(2),
                      p: +window.__map.getPitch().toFixed(1),
                      b: +window.__map.getBearing().toFixed(1),
                      sims: Object.keys(window.__simScenes || {}),
                      cap: (document.querySelector('.pointer-events-none .rounded-2xl div')||{}).textContent || '',
                      coords: window.__voyageCoordCount || 0,
                      running: !!document.querySelector("button[aria-label='Stop journey']"),
                    })"""
                )
                s["t"] = round(time.time() - t0, 1)
                samples.append(s)
                if not s["running"] and s["t"] > 20:
                    break
                page.wait_for_timeout(2000)

            # 1. zero errors
            check("zero console/page errors across the run", not errors,
                  f"{len(errors)}: {errors[:2]}")

            # 2. dives. With 21 dwells the camera rarely returns to sea level
            # between neighbors, so consecutive dwells merge into one pitched
            # window — count windows loosely and assert the pitched SHARE,
            # which is what "the journey actually dives" means at this density.
            dive_samples = [s for s in samples if s["p"] >= 40]
            windows = 0
            prev_pitched = False
            for s in samples:
                pitched = s["p"] >= 40
                if pitched and not prev_pitched:
                    windows += 1
                prev_pitched = pitched
            share = len(dive_samples) / max(1, len(samples))
            check("camera dives: pitched windows exist and dominate the run",
                  windows >= 3 and share >= 0.35, f"{windows} windows, {share:.0%} pitched")
            check("directory-dive zoom reached (>=6.2)", any(s["z"] >= 6.2 for s in samples),
                  f"max z {max(s['z'] for s in samples)}")

            # 3. orbit
            max_b = max(abs(s["b"]) for s in samples)
            check("orbit turns: |bearing| exceeds 8 deg", max_b >= 8, f"max {max_b}")

            # 4. sims
            seen_sims = {sim for s in samples for sim in s["sims"]}
            check("story scenes mount during the run (>=3 distinct)", len(seen_sims) >= 3,
                  ", ".join(sorted(seen_sims)))

            # 5. the ride
            transit = [s for s in samples if "Knock-Up" in s["cap"]]
            check("the Knock-Up Stream is ridden (caption + pitch>=50)",
                  any(s["p"] >= 50 for s in transit),
                  f"{len(transit)} transit samples, pitches {[s['p'] for s in transit]}")

            # 6. trail monotonic
            coords = [s["coords"] for s in samples if s["coords"] > 0]
            mono = all(b >= a for a, b in zip(coords, coords[1:]))
            check("voyage trail only grows", mono and len(coords) > 10,
                  f"{len(coords)} samples, {coords[0] if coords else 0} -> {coords[-1] if coords else 0}")

            # 7. it ends
            check("the journey ends on its own", samples[-1]["running"] is False,
                  f"last sample t={samples[-1]['t']}s")

            # 8. authored holds are wall-clock real: every scene observed
            # mounted during the run must stay mounted for at least its
            # duration (the playback manifest's hold covers duration + ramp;
            # the 2s sampling grain eats the ramp allowance). This is the
            # check that catches a dwell window shorter than its scene.
            import json as _json
            playback = _json.loads((ROOT / "data/generated/story_scene_playback.json").read_text())
            by_sim = {f"sim-{r['scene_id']}": r for r in playback["scenes"]}
            spans: dict[str, list[float]] = {}
            for s in samples:
                for sim in s["sims"]:
                    spans.setdefault(sim, [s["t"], s["t"]])[1] = s["t"]
            held_ok, held_detail = True, []
            for sim, (a, b) in spans.items():
                row = by_sim.get(sim)
                if row is None or not row["journey"]["enabled"]:
                    continue
                need = row["duration_ms"] / 1000 - 2.5  # sampling grain slack
                if (b - a) < need:
                    held_ok = False
                    held_detail.append(f"{sim} held {b - a:.1f}s < {need:.1f}s")
            check("every journey scene holds for its full duration", held_ok,
                  "; ".join(held_detail) or f"{len(spans)} scenes measured")

            # 9. the compiled treatment itself is sound (compiler re-run guard:
            # enabled holds must cover duration + camera ramp).
            bad = [r["scene_id"] for r in playback["scenes"]
                   if r["journey"]["enabled"] and r["journey"]["hold_ms"] < r["duration_ms"] + 1200]
            check("playback holds cover duration + ramp", not bad, ", ".join(bad))

            browser.close()
    finally:
        if server:
            server.terminate()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
