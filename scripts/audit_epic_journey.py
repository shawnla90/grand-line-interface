#!/usr/bin/env python3
"""Accelerated browser proof for the local-only Epic Journey."""

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
            audio_requests: list[str] = []
            page.on("console", lambda message: errors.append(message.text[:200]) if message.type == "error" else None)
            page.on("pageerror", lambda error: errors.append(f"PAGEERROR {error}"))
            page.on(
                "request",
                lambda request: audio_requests.append(request.url)
                if "/audio/epic-journey/" in request.url and request.url.endswith(".mp3")
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
            page.evaluate("window.__epicJourneyRate = 30")
            page.click("button[aria-label='Play Epic Journey with audio']")
            page.wait_for_selector("button[aria-label='Stop Epic Journey']", timeout=5000)

            standard_disabled = page.locator("button[aria-label='Play cinematic journey']").is_disabled()
            captions: set[str] = set()
            chapters: list[int] = []
            t0 = time.time()
            while time.time() - t0 < 25:
                state = page.evaluate(
                    """() => ({
                      running: !!document.querySelector("button[aria-label='Stop Epic Journey']"),
                      caption: (document.querySelector('.pointer-events-none .rounded-2xl div') || {}).textContent || '',
                      chapter: +((document.querySelector("input[aria-label='Chapter']") || {}).value || 1),
                    })"""
                )
                captions.add(state["caption"])
                chapters.append(state["chapter"])
                if not state["running"] and time.time() - t0 > 2:
                    break
                page.wait_for_timeout(250)

            requested_names = {url.rsplit("/", 1)[-1] for url in audio_requests}
            disabled = {"lets-battle.mp3", "one-piece-laugh.mp3", "wendys-mansion.mp3"}
            registry = json.loads((ROOT / "data/epic-audio-cues.json").read_text())
            expected_names = {
                cue["src"].rsplit("/", 1)[-1]
                for cue in registry["cues"]
                if cue.get("enabled", True)
            }
            check("Epic Journey starts from a user gesture", standard_disabled)
            check("the accelerated full run ends", not page.locator("button[aria-label='Stop Epic Journey']").count(), f"{time.time() - t0:.1f}s")
            check("chapter progression reaches the final sea", max(chapters) >= 1125, f"max chapter {max(chapters)}")
            check("captions advance across audio and travel beats", len(captions) >= 12, f"{len(captions)} captions")
            check(
                "all 26 active cues are requested",
                requested_names == expected_names,
                f"{len(requested_names)} files; missing {sorted(expected_names - requested_names)}",
            )
            check("unidentified cues never load", not requested_names.intersection(disabled), str(requested_names.intersection(disabled)))
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

    print(f"\n{9 - len(failures)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
