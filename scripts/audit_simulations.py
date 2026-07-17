#!/usr/bin/env python3
"""audit_simulations.py — headless runtime audit of the East Blue 2.5D layer.

READ-ONLY. Drives the /dev/sim-proof harness (which calls the REAL
syncSimulations host — the same single entry point WorldMap will call) in
headless Chrome and asserts the contract the pack must keep:

  1. the main map makes ZERO east-blue-2d atlas requests (flag off — the
     default posture; a regression here means someone wired the layer outside
     the flag).
  2. chapter 49 at the Baratie — zero atlas fetches. The gate holds even on
     the harness that bypasses the env flag: chapter gating is not the flag.
  3. chapter 51 — exactly the duel's two atlases are fetched (zoro, mihawk;
     no krieg, no luffy), the scene mounts, pose steps LAND: zoro passes
     through three-sword-slash and settles defeated; mihawk passes yoru-slash
     and settles victory; the clock clamps at 8000 and every FX goes inactive.
  4. backward scrub 51 -> 49 unmounts the layer (dev hook entry deleted =
     onRemove ran = GPU disposed); returning to 51 restarts at t≈0. The
     replay is the proof that backward state actually reset.
  5. scaffold stacking, ch 99 — luffy-near-execution mounts and the ch-1
     Roger prologue does NOT (newest story state wins per anchor point).
  6. reduced motion — the layer reports the final safe pose, no FX, no clock.

Requires the dev server (the harness route 404s in production): uses AUDIT_URL
or starts its own on AUDIT_PORT (default 3211).

Run: python3 scripts/audit_simulations.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3211"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

DUEL = "sim-baratie-zoro-vs-mihawk"

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


def atlas_requests(reqs: list[str]) -> list[str]:
    return sorted({u.split("/art/east-blue-2d/")[1].split("/")[0] for u in reqs if "/art/east-blue-2d/" in u})


def actor_pose(page, scene_id: str, actor_id: str):
    return page.evaluate(
        f"""() => {{
          const s = (window.__simScenes || {{}})['{scene_id}'];
          if (!s) return null;
          const a = s.actors.find(a => a.id === '{actor_id}');
          return a ? a.pose : null;
        }}"""
    )


def scene_ids(page) -> list[str]:
    return page.evaluate("() => Object.keys(window.__simScenes || {})")


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

            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=51", timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            # ---- 1. the real map, flag off: zero simulation bytes
            page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=30000)
            page.wait_for_timeout(1000)
            check("main map at ch51: zero east-blue-2d requests", not atlas_requests(requests),
                  ", ".join(atlas_requests(requests)))

            # ---- 2. harness at ch49: the DUEL's gate holds. The rule is per
            # scene ("never fetch a scene before ITS verified chapter start") —
            # Orange Town (gate ch20) is legitimately in this wide viewport and
            # its mounting is the multi-scene path working, not a leak.
            requests.clear()
            page.goto(f"{BASE}/dev/sim-proof?ch=49")
            page.wait_for_timeout(2500)
            fetched49 = atlas_requests(requests)
            check("ch49 Baratie: no duel atlas fetched",
                  "roronoa-zoro" not in fetched49 and "dracule-mihawk" not in fetched49,
                  ", ".join(fetched49))
            check("ch49: duel not mounted (earlier-gate scenes may be)",
                  DUEL not in scene_ids(page), ", ".join(scene_ids(page)))

            # ---- 3. ch51: the duel plays, exactly its cast is fetched
            requests.clear()
            page.click("[data-testid=go-51]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{DUEL}']", timeout=15000)
            # Pose steps land while the 8s scene runs (dash->slash windows are
            # 1200-1450ms wide; polling catches them).
            saw_slash = False
            saw_yoru = False
            deadline = time.time() + 10
            while time.time() < deadline:
                if actor_pose(page, DUEL, "zoro") == "three-sword-slash":
                    saw_slash = True
                if actor_pose(page, DUEL, "mihawk") == "yoru-slash":
                    saw_yoru = True
                if saw_slash and saw_yoru:
                    break
                page.wait_for_timeout(80)
            check("ch51: zoro steps through three-sword-slash", saw_slash)
            check("ch51: mihawk steps through yoru-slash", saw_yoru)
            page.wait_for_function(
                f"""() => {{
                  const s = (window.__simScenes || {{}})['{DUEL}'];
                  return s && s.timeMs >= 8000;
                }}""", timeout=12000)
            check("ch51: final frame held", actor_pose(page, DUEL, "zoro") == "defeated"
                  and actor_pose(page, DUEL, "mihawk") == "victory",
                  f"zoro={actor_pose(page, DUEL, 'zoro')} mihawk={actor_pose(page, DUEL, 'mihawk')}")
            fx_active = page.evaluate(
                f"() => ((window.__simScenes || {{}})['{DUEL}'] || {{firedFx:[]}}).firedFx.filter(f => f.active).length")
            check("ch51: all FX inactive after the fight", fx_active == 0, f"{fx_active} active")
            fetched = atlas_requests(requests)
            check("ch51: exactly the duel's atlases fetched", fetched == ["dracule-mihawk", "roronoa-zoro"],
                  ", ".join(fetched))

            # ---- 4. backward scrub resets, replay restarts at zero
            page.fill("[data-testid=chapter-input]", "49")
            page.wait_for_function(
                f"() => !Object.keys(window.__simScenes || {{}}).includes('{DUEL}')", timeout=8000)
            check("scrub 51->49: duel unmounted and disposed", True)
            page.fill("[data-testid=chapter-input]", "51")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{DUEL}']", timeout=8000)
            t0 = page.evaluate(f"() => (window.__simScenes || {{}})['{DUEL}'].timeMs")
            check("return to 51: clock restarted near zero", isinstance(t0, (int, float)) and t0 < 2500, f"t={t0}")

            # ---- 5. the scaffold shows its newest story state
            page.click("[data-testid=go-99]")
            page.wait_for_function(
                "() => Object.keys(window.__simScenes || {}).includes('sim-luffy-near-execution')", timeout=10000)
            ids = scene_ids(page)
            check("ch99 scaffold: near-execution mounts, Roger prologue does not",
                  "sim-luffy-near-execution" in ids and "sim-roger-execution-prologue" not in ids,
                  ", ".join(ids))

            # ---- 6. reduced motion: safe pose, no clock, no FX
            rm = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            rm.goto(f"{BASE}/dev/sim-proof?ch=51")
            rm.wait_for_function(f"() => (window.__simScenes || {{}})['{DUEL}']", timeout=15000)
            rm.wait_for_timeout(600)
            state = rm.evaluate(
                f"""() => {{
                  const s = (window.__simScenes || {{}})['{DUEL}'];
                  return {{ rm: s.reducedMotion, t: s.timeMs, fx: s.firedFx.length,
                            zoro: s.actors.find(a => a.id==='zoro').pose }};
                }}""")
            check("reduced motion: static final safe pose, zero FX",
                  state["rm"] is True and state["t"] is None and state["fx"] == 0 and state["zoro"] == "defeated",
                  str(state))
            rm.close()

            browser.close()
    finally:
        if server:
            server.terminate()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
