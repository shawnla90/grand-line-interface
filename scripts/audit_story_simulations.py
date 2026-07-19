#!/usr/bin/env python3
"""Headless runtime proof for the disabled-by-default Arabasta story pack.

Drives the real shared syncSimulations host through /dev/sim-proof and checks
chapter gating, signed atlas demand-loading, pose progression, newest-scene
replacement, backward-scrub reset, the Ace/Smoker tableau, and reduced motion.
The extended proof also covers Crocodile round one, Sanji/Bon Clay, and
Zoro/Mr. One with exact lazy-load and final-pose assertions.
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
CROCODILE_SCENE = "sim-arabasta-luffy-vs-crocodile-round-one"
SANJI_SCENE = "sim-arabasta-sanji-vs-bon-clay"
MR_ONE_SCENE = "sim-arabasta-zoro-vs-mr-one"
NAMI_SCENE = "sim-arabasta-nami-vs-miss-doublefinger"
CROCODILE_TWO_SCENE = "sim-arabasta-luffy-vs-crocodile-round-two"
CROCODILE_FINAL_SCENE = "sim-arabasta-luffy-vs-crocodile-final"

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

            requests.clear()
            page.click("[data-testid=go-176]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{CROCODILE_SCENE}']", timeout=10000)
            check("ch176: Crocodile round one mounts at Rainbase", CROCODILE_SCENE in scene_ids(page), ", ".join(scene_ids(page)))
            check(
                "ch176: only Luffy and Crocodile atlases demand-load",
                atlas_requests(requests) == ["crocodile-arabasta-sand", "monkey-d-luffy-crocodile-round-one"],
                ", ".join(atlas_requests(requests)),
            )
            saw_stretch = False
            deadline = time.time() + 7
            while time.time() < deadline:
                if actor_pose(page, CROCODILE_SCENE, "luffy") == "rubber-pistol-stretch":
                    saw_stretch = True
                    break
                page.wait_for_timeout(70)
            check("ch176: Luffy reaches the rubber-pistol stretch", saw_stretch)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{CROCODILE_SCENE}']?.timeMs >= 10000",
                timeout=15000,
            )
            final_crocodile = actor_pose(page, CROCODILE_SCENE, "crocodile")
            final_luffy = actor_pose(page, CROCODILE_SCENE, "luffy")
            check(
                "ch176: Crocodile victory and quicksand aftermath hold",
                (final_crocodile, final_luffy) == ("victorious-aftermath", "quicksand-aftermath"),
                f"crocodile={final_crocodile}, luffy={final_luffy}",
            )

            page.fill("[data-testid=chapter-input]", "175")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{CROCODILE_SCENE}']", timeout=8000)
            check("backward scrub: Crocodile scene unmounted and disposed", True)
            page.fill("[data-testid=chapter-input]", "176")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{CROCODILE_SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{CROCODILE_SCENE}'].timeMs")
            check("return to ch176: Crocodile clock restarts near zero", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            requests.clear()
            page.click("[data-testid=go-187]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SANJI_SCENE}']", timeout=10000)
            check("ch187: Sanji and Bon Clay mount at Alubarna", SANJI_SCENE in scene_ids(page), ", ".join(scene_ids(page)))
            check(
                "ch187: only Sanji and Bon Clay atlases demand-load",
                atlas_requests(requests) == ["bon-clay-mr-two", "sanji-arabasta-bon-clay"],
                ", ".join(atlas_requests(requests)),
            )
            saw_anti_manner = False
            deadline = time.time() + 9
            while time.time() < deadline:
                if actor_pose(page, SANJI_SCENE, "sanji") == "anti-manner-kick-course":
                    saw_anti_manner = True
                    break
                page.wait_for_timeout(70)
            check("ch187: Sanji reaches Anti-Manner Kick Course", saw_anti_manner)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{SANJI_SCENE}']?.timeMs >= 9000",
                timeout=14000,
            )
            final_bon_clay = actor_pose(page, SANJI_SCENE, "bon-clay")
            final_sanji = actor_pose(page, SANJI_SCENE, "sanji")
            check(
                "ch187: Bon Clay defeat and Sanji victory hold",
                (final_bon_clay, final_sanji) == ("defeated-hold", "battered-victory"),
                f"bon-clay={final_bon_clay}, sanji={final_sanji}",
            )

            requests.clear()
            page.click("[data-testid=go-190]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{NAMI_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch190: Nami/Miss Doublefinger replaces Sanji/Bon Clay at Alubarna",
                NAMI_SCENE in ids and SANJI_SCENE not in ids and MR_ONE_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch190: only Nami and Miss Doublefinger atlases demand-load",
                atlas_requests(requests) == ["miss-doublefinger-arabasta", "nami-arabasta-doublefinger"],
                ", ".join(atlas_requests(requests)),
            )
            saw_tornado = False
            deadline = time.time() + 9
            while time.time() < deadline:
                if actor_pose(page, NAMI_SCENE, "nami") == "tornado-tempo":
                    saw_tornado = True
                    break
                page.wait_for_timeout(70)
            check("ch190: Nami reaches Tornado Tempo", saw_tornado)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{NAMI_SCENE}']?.timeMs >= 10000",
                timeout=15000,
            )
            final_doublefinger = actor_pose(page, NAMI_SCENE, "miss-doublefinger")
            final_nami = actor_pose(page, NAMI_SCENE, "nami")
            check(
                "ch190: Miss Doublefinger defeat and Nami victory hold",
                (final_doublefinger, final_nami) == ("defeated-hold", "battered-victory"),
                f"miss-doublefinger={final_doublefinger}, nami={final_nami}",
            )

            requests.clear()
            page.click("[data-testid=go-194]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{MR_ONE_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch194: Zoro/Mr. One replaces Nami/Miss Doublefinger at Alubarna",
                MR_ONE_SCENE in ids and NAMI_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch194: only Zoro and Mr. One atlases demand-load",
                atlas_requests(requests) == ["daz-bones-mr-one", "roronoa-zoro-arabasta-mr-one"],
                ", ".join(atlas_requests(requests)),
            )
            saw_lion_song = False
            deadline = time.time() + 9
            while time.time() < deadline:
                if actor_pose(page, MR_ONE_SCENE, "zoro") == "lion-song-pass":
                    saw_lion_song = True
                    break
                page.wait_for_timeout(70)
            check("ch194: Zoro reaches Lion Song", saw_lion_song)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{MR_ONE_SCENE}']?.timeMs >= 9500",
                timeout=14500,
            )
            final_mr_one = actor_pose(page, MR_ONE_SCENE, "mr-one")
            final_zoro_mr_one = actor_pose(page, MR_ONE_SCENE, "zoro")
            check(
                "ch194: Mr. One defeat and Zoro's collapsed victory hold",
                (final_mr_one, final_zoro_mr_one) == ("defeated-hold", "collapsed-victory"),
                f"mr-one={final_mr_one}, zoro={final_zoro_mr_one}",
            )

            requests.clear()
            page.click("[data-testid=go-198]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{CROCODILE_TWO_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch198: Crocodile round two replaces Zoro/Mr. One at Alubarna",
                CROCODILE_TWO_SCENE in ids and MR_ONE_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch198: only round-two Luffy and Crocodile atlases demand-load",
                atlas_requests(requests) == ["crocodile-arabasta-round-two", "monkey-d-luffy-crocodile-round-two"],
                ", ".join(atlas_requests(requests)),
            )
            saw_aqua_luffy = False
            saw_wet_punch = False
            deadline = time.time() + 10
            while time.time() < deadline:
                pose = actor_pose(page, CROCODILE_TWO_SCENE, "luffy")
                saw_aqua_luffy = saw_aqua_luffy or pose == "aqua-luffy"
                saw_wet_punch = saw_wet_punch or pose == "wet-fist-rubber-punch"
                if saw_aqua_luffy and saw_wet_punch:
                    break
                page.wait_for_timeout(70)
            check("ch198: Luffy reaches Aqua Luffy and the wet-fist punch", saw_aqua_luffy and saw_wet_punch)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{CROCODILE_TWO_SCENE}']?.timeMs >= 11000",
                timeout=16000,
            )
            final_crocodile_two = actor_pose(page, CROCODILE_TWO_SCENE, "crocodile")
            final_luffy_two = actor_pose(page, CROCODILE_TWO_SCENE, "luffy")
            check(
                "ch198: tomb departure and falling-water revival hold",
                (final_crocodile_two, final_luffy_two) == ("tomb-departure", "falling-water-revival"),
                f"crocodile={final_crocodile_two}, luffy={final_luffy_two}",
            )

            page.fill("[data-testid=chapter-input]", "197")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{CROCODILE_TWO_SCENE}']", timeout=8000)
            check("backward scrub: Crocodile round two unmounted and disposed", True)
            page.fill("[data-testid=chapter-input]", "198")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{CROCODILE_TWO_SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{CROCODILE_TWO_SCENE}'].timeMs")
            check("return to ch198: round-two clock restarts near zero", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            requests.clear()
            page.click("[data-testid=go-203]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{CROCODILE_FINAL_SCENE}']", timeout=10000)
            ids = scene_ids(page)
            check(
                "ch203: royal-tomb final replaces Crocodile round two",
                CROCODILE_FINAL_SCENE in ids and CROCODILE_TWO_SCENE not in ids,
                ", ".join(ids),
            )
            check(
                "ch203: only final-round Luffy and Crocodile atlases demand-load",
                atlas_requests(requests) == ["crocodile-arabasta-final", "monkey-d-luffy-crocodile-final"],
                ", ".join(atlas_requests(requests)),
            )
            saw_storm = False
            deadline = time.time() + 11
            while time.time() < deadline:
                if actor_pose(page, CROCODILE_FINAL_SCENE, "luffy") == "gum-gum-storm":
                    saw_storm = True
                    break
                page.wait_for_timeout(70)
            check("ch203: Luffy reaches Gum-Gum Storm", saw_storm)
            page.wait_for_function(
                f"() => (window.__simScenes || {{}})['{CROCODILE_FINAL_SCENE}']?.timeMs >= 11500",
                timeout=16500,
            )
            final_crocodile_tomb = actor_pose(page, CROCODILE_FINAL_SCENE, "crocodile")
            final_luffy_tomb = actor_pose(page, CROCODILE_FINAL_SCENE, "luffy")
            check(
                "ch203: Crocodile defeat and exhausted Luffy victory hold",
                (final_crocodile_tomb, final_luffy_tomb) == ("unconscious-aftermath", "exhausted-victory"),
                f"crocodile={final_crocodile_tomb}, luffy={final_luffy_tomb}",
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
