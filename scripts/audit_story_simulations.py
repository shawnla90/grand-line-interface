#!/usr/bin/env python3
"""Headless runtime proof for the disabled-by-default Arabasta Batch A pack.

Drives the real shared syncSimulations host through /dev/sim-proof and checks
chapter gating, signed atlas demand-loading, pose progression, newest-scene
replacement, backward-scrub reset, the Ace/Smoker tableau, and reduced motion.
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
PACK_PATH = "/art/story-simulations/arabasta-saga-2d-v1/"
ZORO_SCENE = "sim-whisky-peak-zoro-vs-bounty-hunters"
ROBIN_SCENE = "sim-robin-miss-all-sunday-arrival"
ACE_SCENE = "sim-ace-blocks-smoker-at-nanohana"
FLEET_SCENE = "sim-ace-fire-fist-destroys-billions-fleet"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def atlas_requests(requests: list[str]) -> list[str]:
    return sorted({url.split(PACK_PATH)[1].split("/")[0] for url in requests if PACK_PATH in url})


def scene_ids(page) -> list[str]:
    return page.evaluate("() => Object.keys(window.__simScenes || {})")


def actor_pose(page, scene_id: str, actor_id: str):
    return page.evaluate(
        f"""() => {{
          const scene = (window.__simScenes || {{}})['{scene_id}'];
          const actor = scene?.actors.find((item) => item.id === '{actor_id}');
          return actor?.pose ?? null;
        }}"""
    )


def main() -> int:
    server = None
    if "AUDIT_URL" not in os.environ:
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            requests: list[str] = []
            page.on("request", lambda request: requests.append(request.url))

            url = f"{BASE}/dev/sim-proof?pack=arabasta&ch=106"
            for _ in range(60):
                try:
                    page.goto(url, timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            page.wait_for_timeout(1800)
            check("ch106: zero Arabasta atlases fetched", not atlas_requests(requests), ", ".join(atlas_requests(requests)))
            check("ch106: no Arabasta scene mounted", not scene_ids(page), ", ".join(scene_ids(page)))

            requests.clear()
            page.click("[data-testid=go-107]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}']", timeout=15000)
            saw_slash = False
            deadline = time.time() + 10
            while time.time() < deadline:
                if actor_pose(page, ZORO_SCENE, "zoro") == "three-sword-swarm-slash":
                    saw_slash = True
                    break
                page.wait_for_timeout(70)
            check("ch107: Zoro reaches three-sword-swarm-slash", saw_slash)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{ZORO_SCENE}']?.timeMs >= 9000",
                timeout=14000,
            )
            final_zoro = actor_pose(page, ZORO_SCENE, "zoro")
            final_left = actor_pose(page, ZORO_SCENE, "crowd-left")
            final_right = actor_pose(page, ZORO_SCENE, "crowd-right")
            check(
                "ch107: victory tableau holds authored final poses",
                (final_zoro, final_left, final_right) == ("calm-victory", "defeated-left", "defeated-right"),
                f"zoro={final_zoro}, left={final_left}, right={final_right}",
            )
            check(
                "ch107: only Zoro and crowd atlases fetched",
                atlas_requests(requests) == ["baroque-works-whisky-peak-crowd", "roronoa-zoro-whisky-peak"],
                ", ".join(atlas_requests(requests)),
            )

            page.fill("[data-testid=chapter-input]", "106")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{ZORO_SCENE}']", timeout=8000)
            check("backward scrub: Zoro scene unmounted and disposed", True)
            page.fill("[data-testid=chapter-input]", "107")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}'].timeMs")
            check("return to ch107: clock restarts near zero", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            requests.clear()
            page.click("[data-testid=go-114]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ROBIN_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch114: Robin replaces Zoro at the shared Whisky Peak anchor",
                ROBIN_SCENE in ids and ZORO_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch114: Robin atlas demand-loads alone",
                atlas_requests(requests) == ["nico-robin-miss-all-sunday"],
                ", ".join(atlas_requests(requests)),
            )

            requests.clear()
            page.click("[data-testid=go-158]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ACE_SCENE}']", timeout=10000)
            check(
                "ch158: Ace intervention mounts at Nanohana",
                ACE_SCENE in scene_ids(page),
                ", ".join(scene_ids(page)),
            )
            check(
                "ch158: only Ace and Smoker atlases demand-load",
                atlas_requests(requests) == ["portgas-d-ace-arabasta", "smoker-arabasta"],
                ", ".join(atlas_requests(requests)),
            )

            requests.clear()
            page.click("[data-testid=go-159]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{FLEET_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch159: Fire Fist convoy scene replaces the Smoker intervention",
                FLEET_SCENE in ids and ACE_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch159: only the new convoy atlas demand-loads",
                atlas_requests(requests) == ["baroque-works-ship-convoy"],
                ", ".join(atlas_requests(requests)),
            )
            saw_impact = False
            deadline = time.time() + 7
            while time.time() < deadline:
                if actor_pose(page, FLEET_SCENE, "billions-convoy") == "fire-fist-impact":
                    saw_impact = True
                    break
                page.wait_for_timeout(70)
            check("ch159: convoy reaches the Fire Fist impact pose", saw_impact)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{FLEET_SCENE}']?.timeMs >= 9000",
                timeout=14000,
            )
            final_convoy = actor_pose(page, FLEET_SCENE, "billions-convoy")
            final_ace = actor_pose(page, FLEET_SCENE, "ace")
            check(
                "ch159: burning wreckage and Ace departure hold",
                (final_convoy, final_ace) == ("burning-wreckage", "confident-departure"),
                f"convoy={final_convoy}, ace={final_ace}",
            )

            reduced = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            reduced.goto(f"{BASE}/dev/sim-proof?pack=arabasta&ch=107")
            reduced.wait_for_function(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}']", timeout=15000)
            state = reduced.evaluate(
                f"""() => {{
                  const scene = (window.__simScenes || {{}})['{ZORO_SCENE}'];
                  return {{
                    reduced: scene.reducedMotion,
                    time: scene.timeMs,
                    fx: scene.firedFx.length,
                    zoro: scene.actors.find((actor) => actor.id === 'zoro').pose,
                  }};
                }}"""
            )
            check(
                "reduced motion: final safe pose with zero clock and FX",
                state == {"reduced": True, "time": None, "fx": 0, "zoro": "calm-victory"},
                str(state),
            )
            reduced.close()
            browser.close()
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
