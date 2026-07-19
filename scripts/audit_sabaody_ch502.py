#!/usr/bin/env python3
"""Browser proof for the chapter-502 Sabaody auction-house simulation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3221"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")
PACK_PATH = "/art/story-simulations/sabaody-saga-2d-v1/"
SCENE = "sim-sabaody-luffy-punches-charloss"
AUDIO_SCENE = "sabaody-luffy-punches-charloss"
PROOF = ROOT / "blender-assets/research/story-scenes/sabaody-chapter-502-browser-proof.json"

PASS = 0
FAIL = 0
ROWS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    ROWS.append({"name": name, "pass": ok, "detail": detail})
    if ok:
        PASS += 1
    else:
        FAIL += 1


def atlas_requests(requests: list[str]) -> list[str]:
    return sorted({url.split(PACK_PATH)[1].split("/")[0] for url in requests if PACK_PATH in url})


def scene_ids(page) -> list[str]:
    return page.evaluate("() => Object.keys(window.__simScenes || {})")


def actor_pose(page, actor_id: str):
    return page.evaluate(
        f"""() => (window.__simScenes || {{}})['{SCENE}']
          ?.actors.find((item) => item.id === '{actor_id}')?.pose ?? null"""
    )


def wait_pose(page, actor_id: str, pose: str, timeout_ms: int) -> bool:
    try:
        page.wait_for_function(
            f"""() => (window.__simScenes || {{}})['{SCENE}']
              ?.actors.find((item) => item.id === '{actor_id}')?.pose === '{pose}'""",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def main() -> int:
    server = None
    if "AUDIT_URL" not in os.environ:
        env = os.environ.copy()
        enabled = {part for part in env.get("NEXT_PUBLIC_STORY_SIMULATION_PACKS", "").split(",") if part}
        enabled.update({"arabasta", "skypiea", "enies-lobby", "sabaody"})
        env["NEXT_PUBLIC_STORY_SIMULATION_PACKS"] = ",".join(sorted(enabled))
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    errors: list[str] = []
    requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("request", lambda request: requests.append(request.url))
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

            url = f"{BASE}/dev/sim-proof?pack=sabaody&ch=501"
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
            check("ch501 fetches zero Sabaody atlases", not atlas_requests(requests), ", ".join(atlas_requests(requests)))
            check("ch501 mounts no Sabaody scene", SCENE not in scene_ids(page), ", ".join(scene_ids(page)))

            page.click("[data-testid=sound-unlock]")
            requests.clear()
            page.click("[data-testid=go-502]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SCENE}']", timeout=15000)
            expected = [
                "monkey-d-luffy-sabaody-auction",
                "octy-sabaody-auction",
                "saint-charloss-sabaody-auction",
            ]
            check("ch502 loads exactly the three signed atlases", atlas_requests(requests) == expected, ", ".join(atlas_requests(requests)))
            check("Hatchan warns Luffy while wounded", wait_pose(page, "octy", "warning-luffy", 5000))
            check("Luffy crosses into the silent lunge", wait_pose(page, "luffy", "silent-lunge", 7000))
            check("Luffy reaches the full-extension punch", wait_pose(page, "luffy", "full-extension-punch", 5000))
            check("Charloss reaches face impact", actor_pose(page, "charloss") == "face-impact", actor_pose(page, "charloss") or "none")

            try:
                page.wait_for_function(
                    f"""() => ((window.__simScenes || {{}})['{SCENE}']?.rigs || [])
                      .some((rig) => rig.gamma < 0.85 && rig.gain > 1.2)""",
                    timeout=3500,
                )
                gamma_hit = True
            except Exception:
                gamma_hit = False
            check("actor-only gamma/gain envelope peaks on contact", gamma_hit)

            try:
                page.wait_for_function(
                    f"""() => ((window.__simAudio || {{ fired: [] }}).fired || [])
                      .some((item) => item.sceneId === '{AUDIO_SCENE}' && item.bindingId === 'charloss-impact')""",
                    timeout=5000,
                )
            except Exception:
                pass
            fired = page.evaluate(
                f"""() => ((window.__simAudio || {{ fired: [] }}).fired || [])
                  .filter((item) => item.sceneId === '{AUDIO_SCENE}')
                  .map((item) => item.bindingId)"""
            )
            check("impact audio fires once on the authored blow", fired.count("charloss-impact") == 1, ", ".join(fired))

            check("Hatchan reaches the safe collapse", wait_pose(page, "octy", "relieved-collapse", 6000))
            check("Charloss holds the defeated fall", actor_pose(page, "charloss") == "defeated-fall", actor_pose(page, "charloss") or "none")

            requests.clear()
            page.click("[data-testid=go-503]")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SCENE}']?.timeMs === null", timeout=8000)
            check(
                "ch503 keeps only the frozen aftermath tableau",
                actor_pose(page, "octy") == "relieved-collapse" and actor_pose(page, "charloss") == "defeated-fall",
                f"hatchan={actor_pose(page, 'octy')}, charloss={actor_pose(page, 'charloss')}",
            )
            check("ch503 fetches no new atlas or audio", not requests, ", ".join(requests[:3]))

            page.fill("[data-testid=chapter-input]", "501")
            page.wait_for_function(f"() => !(window.__simScenes || {{}})['{SCENE}']", timeout=8000)
            page.fill("[data-testid=chapter-input]", "502")
            page.wait_for_function(f"() => (window.__simScenes || {{}})['{SCENE}']", timeout=8000)
            restarted = page.evaluate(f"() => (window.__simScenes || {{}})['{SCENE}'].timeMs")
            check("scrub below the gate then re-enter restarts the clock", isinstance(restarted, (int, float)) and restarted < 2500, f"t={restarted}")

            reduced = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            reduced.goto(f"{BASE}/dev/sim-proof?pack=sabaody&ch=502", timeout=15000)
            reduced.wait_for_function(f"() => (window.__simScenes || {{}})['{SCENE}']", timeout=15000)
            reduced_state = reduced.evaluate(f"() => (window.__simScenes || {{}})['{SCENE}'].reducedMotion")
            reduced_time = reduced.evaluate(f"() => (window.__simScenes || {{}})['{SCENE}'].timeMs")
            reduced_poses = reduced.evaluate(
                f"() => Object.fromEntries((window.__simScenes || {{}})['{SCENE}'].actors.map((actor) => [actor.id, actor.pose]))"
            )
            check("reduced motion freezes on the safe final tableau", reduced_state is True and reduced_time is None, f"poses={reduced_poses}")
            check("browser reports no runtime errors", not errors, " | ".join(errors[:4]))

            reduced.close()
            browser.close()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps({
        "schema_version": 1,
        "pack_id": "sabaody-saga-2d-v1",
        "route": "/dev/sim-proof?pack=sabaody&ch=501",
        "checks": ROWS,
        "summary": {"passes": PASS, "failures": FAIL},
    }, indent=2) + "\n")
    print(f"\n{PASS}/{PASS + FAIL} checks pass")
    print(PROOF.relative_to(ROOT))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
