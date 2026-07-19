#!/usr/bin/env python3
"""Live-browser proof for Reverse Mountain chapters 100-105."""

from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright


BASE = os.environ.get("AUDIT_URL", "http://localhost:3000")
ASSET = "reverse-mountain-twin-cape-voyage"
LAYER = f"glb-{ASSET}"
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    passed = bool(ok)
    print(f"  [{'ok ' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    PASS += int(passed)
    FAIL += int(not passed)


def set_chapter(page, chapter: int) -> None:
    page.locator("input[type=range][aria-label='Chapter']").evaluate(
        """(el, value) => {
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(el, String(value));
          el.dispatchEvent(new Event('input', {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
        }""",
        chapter,
    )
    page.wait_for_function(
        "([value]) => document.querySelector(\"input[type=range][aria-label='Chapter']\")?.value === String(value)",
        arg=[chapter],
        timeout=15000,
    )
    page.wait_for_timeout(1400)


def component_state(page) -> dict[str, bool]:
    return page.evaluate(
        """([layer]) => {
          const scene = window.__glbScenes?.[layer];
          const out = {};
          scene?.traverse((obj) => {
            if (obj.userData?.component_id) out[obj.userData.component_id] = obj.visible;
          });
          return out;
        }""",
        [LAYER],
    )


def open_local_theatre(page) -> None:
    page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=60000)
    # Manual chapter-gate inspection keeps the camera parked on the local
    # theatre. The cinematic journey uses its authored moment focus instead.
    page.locator("button[title='Camera follows the ship (F)']").click()
    page.evaluate(
        """() => {
          if (window.__map.getProjection().type !== 'mercator') window.__map.setProjection({type:'mercator'});
          window.__map.jumpTo({center:[-179,-2], zoom:6.4, pitch:48, bearing:0});
        }"""
    )
    page.wait_for_timeout(1200)


def run_normal(browser) -> None:
    requests: list[str] = []
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors: list[str] = []
    page.on("request", lambda req: requests.append(req.url) if ASSET in req.url else None)
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(f"{BASE}/?ch=100", wait_until="domcontentloaded", timeout=60000)
    open_local_theatre(page)

    check("chapter 100 keeps the GLB absent", page.evaluate("([id]) => !window.__map.getLayer(id)", [LAYER]))
    check("chapter 100 fetches no Reverse Mountain GLB", not any(url.endswith(".glb") for url in requests))

    set_chapter(page, 101)
    page.wait_for_function("([id]) => !!window.__glbScenes?.[id]", arg=[LAYER], timeout=60000)
    clips = page.evaluate("([id]) => window.__glbClipNames?.[id] || []", [LAYER])
    state = component_state(page)
    check("all 21 named clips reach Three.js", len(clips) == 21, f"{len(clips)} clips")
    check("chapter 101 shows massif/current/Merry", all(state.get(k) for k in ["reverse-mountain-massif", "east-blue-ascent-current", "going-merry"]))
    check("chapter 101 withholds Twin Cape and whale", not state.get("twin-cape") and not state.get("laboon-unidentified"))
    label = page.evaluate("([id]) => window.__runtimeAssetLabels?.[id]?.laboon ?? null", [ASSET])
    check("chapter 101 has no whale identity label", label is None)

    set_chapter(page, 102)
    state = component_state(page)
    label = page.evaluate("([id]) => window.__runtimeAssetLabels?.[id]?.laboon ?? null", [ASSET])
    animation = page.evaluate("([id]) => window.__glbAnimationState?.[id] || null", [LAYER])
    check("chapter 102 reveals Twin Cape and giant whale", state.get("twin-cape") and state.get("laboon-unidentified"), str(state))
    check("chapter 102 label is spoiler-safe", label == "Unidentified giant whale", str(label))
    check("chapter 102 keeps lighthouse and Crocus hidden", not state.get("twin-cape-lighthouse") and not state.get("crocus"))
    check("chapter 102 runs contact animation", animation and animation["chapter"] == 102 and animation["animate"], str(animation))

    set_chapter(page, 103)
    state = component_state(page)
    label = page.evaluate("([id]) => window.__runtimeAssetLabels?.[id]?.laboon ?? null", [ASSET])
    check("chapter 103 reveals Laboon, Crocus, and lighthouse", label == "Laboon" and state.get("crocus") and state.get("twin-cape-lighthouse"))
    check("chapter 103 opens only the verified interior window", state.get("laboon-interior-theatre") is True)

    set_chapter(page, 104)
    state = component_state(page)
    animation = page.evaluate("([id]) => window.__glbAnimationState?.[id] || null", [LAYER])
    check("chapter 104 closes the interior inset again", state.get("laboon-interior-theatre") is False)
    check("chapter 104 runs the promise tableau", animation and "laboon_promise_response" in animation["clips"], str(animation))
    check("unverified whirlpool never appears", state.get("local-whirlpool-emitter") is False)

    set_chapter(page, 105)
    animation = page.evaluate("([id]) => window.__glbAnimationState?.[id] || null", [LAYER])
    check("chapter 105 runs Merry departure", animation and "merry_twin_cape_departure" in animation["clips"], str(animation))

    # Backward scrub must re-fog already-loaded GPU nodes.
    set_chapter(page, 101)
    state = component_state(page)
    check("backward scrub re-hides Twin Cape/Laboon/Crocus", not state.get("twin-cape") and not state.get("laboon-unidentified") and not state.get("crocus"))

    # Move outside the hysteresis radius: the layer and GPU scene must dispose.
    page.evaluate("() => window.__map.jumpTo({center:[-120,0], zoom:6.4, pitch:48})")
    page.wait_for_timeout(1500)
    check("offscreen local theatre unloads", page.evaluate("([id]) => !window.__map.getLayer(id) && !window.__glbScenes?.[id]", [LAYER]))
    check("Reverse Mountain GLB fetched exactly once before unload", len([url for url in requests if url.endswith(".glb")]) == 1, str(requests))
    check("zero browser errors", not errors, str(errors[:3]))
    page.close()


def run_reduced(browser) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(f"{BASE}/?ch=105", wait_until="domcontentloaded", timeout=60000)
    open_local_theatre(page)
    page.wait_for_function("([id]) => !!window.__glbAnimationState?.[id]", arg=[LAYER], timeout=60000)
    animation = page.evaluate("([id]) => window.__glbAnimationState[id]", [LAYER])
    check("reduced motion freezes the voyage clock", animation["animate"] is False, str(animation))
    check("reduced motion lands on departure-safe final clips", "merry_twin_cape_departure" in animation["clips"], str(animation))
    context.close()


def main() -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        run_normal(browser)
        run_reduced(browser)
        browser.close()
    print(f"\n{PASS}/{PASS + FAIL} checks pass")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
