#!/usr/bin/env python3
"""Browser proof for the Skypiea and Enies Lobby climax packs.

Exercises the real syncSimulations host and scene-audio bridge through the
dev-only /dev/sim-proof route. The proof covers chapter gates, lazy atlas
loading, authored pose progression, backward-scrub reset, reduced motion, and
the Gear Second, Diable Jambe, Asura, and Jet Gatling callouts firing on their
matching authored visual events.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3217"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

SKY_PACK_PATH = "/art/story-simulations/skypiea-saga-2d-v1/"
ENIES_PACK_PATH = "/art/story-simulations/enies-lobby-saga-2d-v1/"
SKY_SCENE = "sim-skypiea-luffy-vs-enel"
BLUENO_SCENE = "sim-enies-lobby-luffy-vs-blueno"
SANJI_SCENE = "sim-enies-lobby-sanji-vs-jabra"
ZORO_SCENE = "sim-enies-lobby-zoro-vs-kaku"
LUCCI_SCENE = "sim-enies-lobby-luffy-vs-rob-lucci"
BLUENO_AUDIO_SCENE = "enies-lobby-luffy-vs-blueno"
SANJI_AUDIO_SCENE = "enies-lobby-sanji-vs-jabra"
ZORO_AUDIO_SCENE = "enies-lobby-zoro-vs-kaku"
LUCCI_AUDIO_SCENE = "enies-lobby-luffy-vs-rob-lucci"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


def atlas_requests(requests: list[str], prefix: str) -> list[str]:
    return sorted({url.split(prefix)[1].split("/")[0] for url in requests if prefix in url})


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


def wait_pose(page, scene_id: str, actor_id: str, pose: str, timeout_ms: int = 10000) -> bool:
    try:
        page.wait_for_function(
            f"""() => {{
              const scene = (window.__simScenes || {{}})['{scene_id}'];
              return scene?.actors.find((item) => item.id === '{actor_id}')?.pose === '{pose}';
            }}""",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def fired_bindings(page, scene_id: str) -> list[str]:
    return page.evaluate(
        f"""() => ((window.__simAudio || {{ fired: [] }}).fired || [])
          .filter((item) => item.sceneId === '{scene_id}')
          .map((item) => item.bindingId)"""
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

            url = f"{BASE}/dev/sim-proof?pack=skypiea&ch=278"
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
            check("Skypiea ch278: gate fetches zero atlases", not atlas_requests(requests, SKY_PACK_PATH))
            check("Skypiea ch278: no scene mounts", SKY_SCENE not in scene_ids(page), ", ".join(scene_ids(page)))

            requests.clear()
            page.click("[data-testid=go-279]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SKY_SCENE}']", timeout=15000)
            check(
                "Skypiea ch279: only Luffy and Enel atlases load",
                atlas_requests(requests, SKY_PACK_PATH) == ["enel-skypiea", "monkey-d-luffy-skypiea-enel"],
                ", ".join(atlas_requests(requests, SKY_PACK_PATH)),
            )
            check("Enel lightning meets Luffy's rubber immunity", wait_pose(page, SKY_SCENE, "luffy", "lightning-immunity-laugh", 7000))
            check("Luffy carries the separate gold-ball burden pose", wait_pose(page, SKY_SCENE, "luffy", "gold-ball-burden", 7000))
            check("Luffy launches the Golden Rifle", wait_pose(page, SKY_SCENE, "luffy", "golden-rifle-launch", 7000))
            check("Enel reaches the golden-bell defeat", wait_pose(page, SKY_SCENE, "enel", "golden-bell-defeat", 7000))
            check("Skypiea holds the bell-ring victory tableau", wait_pose(page, SKY_SCENE, "luffy", "bell-ring-victory", 5000))

            page.fill("[data-testid=chapter-input]", "278")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{SKY_SCENE}']", timeout=8000)
            check("Skypiea backward scrub disposes the scene", True)
            page.fill("[data-testid=chapter-input]", "279")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SKY_SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{SKY_SCENE}'].timeMs")
            check("Skypiea re-entry restarts near zero", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            requests.clear()
            page.click("[data-testid=go-386]")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{SKY_SCENE}']", timeout=8000)
            page.wait_for_timeout(500)
            check("Enies Lobby ch386: gate fetches zero atlases", not atlas_requests(requests, ENIES_PACK_PATH))
            check("Enies Lobby ch386: no scene mounts", not scene_ids(page), ", ".join(scene_ids(page)))

            page.click("[data-testid=sound-unlock]")
            page.wait_for_function("() => window.__simAudio?.unlocked === true", timeout=5000)
            requests.clear()
            page.click("[data-testid=go-387]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{BLUENO_SCENE}']", timeout=15000)
            check(
                "Enies Lobby ch387: only Luffy and Blueno atlases load",
                atlas_requests(requests, ENIES_PACK_PATH) == ["blueno-enies-lobby", "monkey-d-luffy-enies-lobby-blueno"],
                ", ".join(atlas_requests(requests, ENIES_PACK_PATH)),
            )
            check("Luffy visibly activates Gear Second", wait_pose(page, BLUENO_SCENE, "luffy", "gear-second-activation", 5000))
            check("Gear Second progresses into Jet Pistol", wait_pose(page, BLUENO_SCENE, "luffy", "jet-pistol-rush", 5000))
            check("Blueno takes the Jet Bazooka finish", wait_pose(page, BLUENO_SCENE, "blueno", "jet-bazooka-defeat", 5000))
            try:
                page.wait_for_function(
                    f"() => ((window.__simAudio || {{ fired: [] }}).fired || []).some((item) => item.sceneId === '{BLUENO_AUDIO_SCENE}' && item.bindingId === 'gear-second-call')",
                    timeout=5000,
                )
            except Exception:
                pass
            bindings = fired_bindings(page, BLUENO_AUDIO_SCENE)
            check("Gear Second call fires once on activation", bindings.count("gear-second-call") == 1, ", ".join(bindings))
            check("Gear Second audio is requested after unlock", any("/audio/epic-journey/gear-second-monkey-d.mp3" in url for url in requests))

            requests.clear()
            page.click("[data-testid=go-414]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{BLUENO_SCENE}']?.timeMs === null", timeout=8000)
            check(
                "Enies Lobby ch414: Blueno fight holds as a finished tableau",
                actor_pose(page, BLUENO_SCENE, "luffy") == "victory-stance"
                and actor_pose(page, BLUENO_SCENE, "blueno") == "collapsed-defeat",
                f"luffy={actor_pose(page, BLUENO_SCENE, 'luffy')}, blueno={actor_pose(page, BLUENO_SCENE, 'blueno')}",
            )
            check("Finished Blueno tableau requests no new atlas or audio", not requests)
            page.click("[data-testid=go-415]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SANJI_SCENE}']", timeout=15000)
            check(
                "Enies Lobby ch415: only Sanji and Jabra atlases load",
                atlas_requests(requests, ENIES_PACK_PATH) == ["jabra-enies-lobby", "sanji-enies-lobby-jabra"],
                ", ".join(atlas_requests(requests, ENIES_PACK_PATH)),
            )
            check("Sanji's opening remains a flame-free kick", wait_pose(page, SANJI_SCENE, "sanji", "collier-kick", 5000))
            check("Sanji visibly ignites first Diable Jambe", wait_pose(page, SANJI_SCENE, "sanji", "diable-jambe-ignite", 7000))
            check("Sanji reaches Flambage Shot", wait_pose(page, SANJI_SCENE, "sanji", "flambage-shot", 5000))
            try:
                page.wait_for_function(
                    f"() => ((window.__simAudio || {{ fired: [] }}).fired || []).some((item) => item.sceneId === '{SANJI_AUDIO_SCENE}' && item.bindingId === 'diable-jambe-call')",
                    timeout=5000,
                )
            except Exception:
                pass
            bindings = fired_bindings(page, SANJI_AUDIO_SCENE)
            check("Diable Jambe call fires once on ignition", bindings.count("diable-jambe-call") == 1, ", ".join(bindings))
            check("Diable Jambe audio is requested after unlock", any("/audio/epic-journey/one-piece-sanji-diable.mp3" in url for url in requests))

            requests.clear()
            page.click("[data-testid=go-416]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}']", timeout=15000)
            check(f"Chapter 416 replaces Sanji/Jabra with Zoro/Kaku", SANJI_SCENE not in scene_ids(page), ", ".join(scene_ids(page)))
            check(
                "Enies Lobby ch416: only Zoro and Kaku atlases load",
                atlas_requests(requests, ENIES_PACK_PATH) == ["kaku-enies-lobby", "roronoa-zoro-enies-lobby-kaku"],
                ", ".join(atlas_requests(requests, ENIES_PACK_PATH)),
            )
            check("Kaku reaches Four-Sword Style", wait_pose(page, ZORO_SCENE, "kaku", "four-sword-style", 5000))
            check("Zoro manifests Asura", wait_pose(page, ZORO_SCENE, "zoro", "asura-manifestation", 7000))
            check("Zoro reaches the nine-sword finish", wait_pose(page, ZORO_SCENE, "zoro", "nine-sword-asura-strike", 5000))
            try:
                page.wait_for_function(
                    f"() => ((window.__simAudio || {{ fired: [] }}).fired || []).some((item) => item.sceneId === '{ZORO_AUDIO_SCENE}' && item.bindingId === 'asura-santoryu-call')",
                    timeout=5000,
                )
            except Exception:
                pass
            bindings = fired_bindings(page, ZORO_AUDIO_SCENE)
            check("Santoryu call fires once on Asura", bindings.count("asura-santoryu-call") == 1, ", ".join(bindings))

            requests.clear()
            page.click("[data-testid=go-418]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}']", timeout=15000)
            check("Chapter 418 replaces Zoro/Kaku with Luffy/Lucci", ZORO_SCENE not in scene_ids(page), ", ".join(scene_ids(page)))
            check(
                "Enies Lobby ch418: only Luffy and Lucci atlases load",
                atlas_requests(requests, ENIES_PACK_PATH) == ["monkey-d-luffy-enies-lobby-lucci", "rob-lucci-enies-lobby"],
                ", ".join(atlas_requests(requests, ENIES_PACK_PATH)),
            )
            check("Gear Second progresses into Jet Pistol", wait_pose(page, LUCCI_SCENE, "luffy", "jet-pistol", 7000))
            check("Gear Third giant arm is distinct", wait_pose(page, LUCCI_SCENE, "luffy", "gear-third-giant-arm", 7000))
            check("Lucci reaches Rokuogan", wait_pose(page, LUCCI_SCENE, "lucci", "rokuogan-shockwave", 5000))
            check("Luffy reaches the Jet Gatling barrage", wait_pose(page, LUCCI_SCENE, "luffy", "jet-gatling-barrage", 5000))
            check("Lucci takes the matching Jet Gatling defeat", actor_pose(page, LUCCI_SCENE, "lucci") == "jet-gatling-defeat", actor_pose(page, LUCCI_SCENE, "lucci") or "none")
            try:
                page.wait_for_function(
                    f"() => ((window.__simAudio || {{ fired: [] }}).fired || []).some((item) => item.sceneId === '{LUCCI_AUDIO_SCENE}' && item.bindingId === 'jet-gatling-call')",
                    timeout=5000,
                )
            except Exception:
                pass
            bindings = fired_bindings(page, LUCCI_AUDIO_SCENE)
            check("Jet Gatling callout fires once on the Lucci barrage", bindings.count("jet-gatling-call") == 1, ", ".join(bindings))
            check("Gatling audio asset is requested only after unlock and scene entry", any("/audio/epic-journey/luffy-gatling.mp3" in url for url in requests))
            check("Luffy holds the exhausted victory", wait_pose(page, LUCCI_SCENE, "luffy", "exhausted-victory", 7000))

            page.fill("[data-testid=chapter-input]", "417")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{ZORO_SCENE}'] && !(window.__simScenes || {{}})['{LUCCI_SCENE}']", timeout=8000)
            check("Enies Lobby backward scrub replaces Lucci with Zoro/Kaku", True)
            page.fill("[data-testid=chapter-input]", "418")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}'].timeMs")
            check("Enies Lobby re-entry restarts near zero", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            reduced = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            reduced_requests: list[str] = []
            reduced.on("request", lambda request: reduced_requests.append(request.url))
            reduced.goto(f"{BASE}/dev/sim-proof?pack=enies-lobby&ch=418", timeout=15000)
            reduced.wait_for_function(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}']", timeout=15000)
            reduced_state = reduced.evaluate(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}'].reducedMotion")
            reduced_time = reduced.evaluate(f"() => (window.__simScenes || {{}})['{LUCCI_SCENE}'].timeMs")
            reduced_luffy = actor_pose(reduced, LUCCI_SCENE, "luffy")
            reduced_lucci = actor_pose(reduced, LUCCI_SCENE, "lucci")
            check("Reduced motion freezes the scene clock", reduced_state is True and reduced_time is None, f"state={reduced_state}, t={reduced_time}")
            check(
                "Reduced motion renders the safe final tableau",
                (reduced_luffy, reduced_lucci) == ("exhausted-victory", "jet-gatling-defeat"),
                f"luffy={reduced_luffy}, lucci={reduced_lucci}",
            )
            check(
                "Reduced motion performs no Gatling audio request",
                not any("/audio/epic-journey/luffy-gatling.mp3" in url for url in reduced_requests),
            )

            reduced.close()
            browser.close()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    print(f"\n{PASS}/{PASS + FAIL} checks pass")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
