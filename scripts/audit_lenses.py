#!/usr/bin/env python3
"""audit_lenses.py — headless runtime audit of the presence lenses (Phase 6A).

READ-ONLY. Drives the real app in headless Chrome and asserts the spoiler
contract the lenses must keep:

  1. ch 1, fruit lens  — no late-game entity or fruit NAME anywhere in the page,
     and no presence feature carries a fruitName/fruitType/hakiTypes property.
  2. ch 550, fruit lens — every feature that carries a fruitType has an authored
     reveal with from_chapter <= 550; entities without a revealed fruit carry NO
     fruit keys at all (absent, not null); zero-holder types have no legend chip.
  3. backward scrub 550 -> 1 (live, in-page) — the DOM re-fogs: no revealed
     names or power props survive.
  4. ch 700, fruit lens — hovering a revealed-fruit orb shows its fruit line.
  5. ch 550, lens=off  — the presence source is empty (the absorbed toggle).
  6. ch 550, haki lens — legend chips only for haki types with revealed users.
  7. crews come and GO — Baroque Works is charted at 200 and gone by 430 (it
     dissolves at 211); CP9 does not exist to the reader at 200, is charted at
     430, and un-renders on a backward scrub to 100.
  8. the Navy is on the chart, in its own ink — the admirals are at Marineford
     at 560 and none of them exists before Loguetown.

Requires the dev server (window.__map is dev-only): the script starts its own
on AUDIT_PORT (default 3210) unless AUDIT_URL is set.

Run: python3 scripts/audit_lenses.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3210"))
BASE = os.environ.get("AUDIT_URL", f"http://localhost:{PORT}")

# Story facts that must NEVER be in the page at chapter 1 (all reveal later).
BANNED_AT_CH1 = [
    "Gura Gura", "Yami Yami", "Mera Mera", "Soru Soru", "Mochi Mochi",
    "Edward Newgate", "Kaido", "Katakuri", "Marshall D. Teach",
    "Doflamingo", "Hancock", "Trafalgar Law",
]

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


def wait_map(page) -> None:
    page.wait_for_function("() => window.__map && window.__map.loaded()", timeout=30000)
    page.wait_for_timeout(400)


def body_text(page) -> str:
    """The RENDERED text — the spoiler contract is about what a reader sees.
    page.content() would include Next's flight payload, which (like any SPA's
    data) carries the full World for the client to gate; that is Phase 5's
    established boundary, unchanged here."""
    return page.evaluate("() => document.body.innerText")


def presence_props(page) -> list[dict]:
    return page.evaluate(
        """() => (window.__map.querySourceFeatures('presence') || [])
                 .map(f => f.properties)"""
    )


def main() -> int:
    reveals = json.loads((ROOT / "canon" / "fruit_reveals.json").read_text())["reveals"]
    reveal_by_slug = {r["slug"]: r for r in reveals}

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

            # Wait for the dev server.
            for _ in range(60):
                try:
                    page.goto(f"{BASE}/?ch=1&lens=fruit", timeout=5000)
                    break
                except Exception:
                    time.sleep(1)
            else:
                print("dev server never came up", file=sys.stderr)
                return 1

            # ---- 1. chapter 1, fruit lens: nothing leaked
            wait_map(page)
            content = body_text(page)
            leaked = [b for b in BANNED_AT_CH1 if b in content]
            check("ch1/fruit: no late-game names in DOM", not leaked, ", ".join(leaked))
            props = presence_props(page)
            dirty = [pr["slug"] for pr in props
                     if "fruitName" in pr or "fruitType" in pr or "hakiTypes" in pr]
            check("ch1/fruit: no power props on any feature", not dirty, ", ".join(dirty))
            fruit_words = [w for w in ("Paramecia", "Logia", "Mythical Zoan") if w in content]
            check("ch1/fruit: no fruit-type chips", not fruit_words, ", ".join(fruit_words))

            # ---- 2. chapter 550, fruit lens: revealed-only props, gated against canon
            page.goto(f"{BASE}/?ch=550&lens=fruit")
            wait_map(page)
            props = presence_props(page)
            with_fruit = [pr for pr in props if "fruitType" in pr]
            check("ch550/fruit: at least one revealed fruit on the board", len(with_fruit) > 0,
                  f"{len(with_fruit)} features")
            bad_gate = []
            for pr in with_fruit:
                r = reveal_by_slug.get(pr["slug"])
                if r is None or r["from_chapter"] > 550 or r["fruit_name"] != pr["fruitName"]:
                    bad_gate.append(pr["slug"])
            check("ch550/fruit: every fruit prop matches an authored reveal <= 550",
                  not bad_gate, ", ".join(bad_gate))
            ungated = [pr["slug"] for pr in props
                       if "fruitType" not in pr and pr.get("fruitName") is not None]
            check("ch550/fruit: unrevealed entities carry NO fruit keys", not ungated,
                  ", ".join(ungated))
            check("ch550/fruit: no chip for zero-holder types (SMILE reveals at 943)",
                  "SMILE" not in body_text(page))

            # ---- 3. live backward scrub 550 -> 1 re-fogs the DOM
            page.keyboard.press("Escape")
            for _ in range(24):
                page.keyboard.press("Shift+ArrowLeft")
            page.wait_for_timeout(2200)  # let the sweep settle
            props = presence_props(page)
            dirty = [pr["slug"] for pr in props if "fruitName" in pr or "hakiTypes" in pr]
            check("scrub->1: no power props survive", not dirty, ", ".join(dirty))
            content = body_text(page)
            leaked = [b for b in BANNED_AT_CH1 if b in content]
            check("scrub->1: DOM re-fogged (no revealed names remain)", not leaked,
                  ", ".join(leaked))

            # ---- 4. tooltip shows the fruit line once revealed.
            # Pick a target whose pixel has exactly ONE rendered hit: orbs overlap,
            # so hovering a chosen entity's coordinate can land on whoever is stacked
            # on top, and then the test is asking about a different character than the
            # tooltip is answering about. Requiring an unambiguous pixel keeps this a
            # test of the tooltip, not of z-order.
            # ch. 700 rather than the war at 570: Marineford draws in every admiral,
            # Warlord and Emperor at once (72 entities, 0 of them on a clean pixel),
            # so the check could only ever reach its negative branch there.
            page.goto(f"{BASE}/?ch=700&lens=fruit")
            wait_map(page)
            target = page.evaluate(
                """() => {
                     const m = window.__map;
                     const feats = m.querySourceFeatures('presence') || [];
                     let fallback = null;
                     for (const f of feats) {
                       const p = m.project(f.geometry.coordinates);
                       const hits = m.queryRenderedFeatures([p.x, p.y], { layers: ['presence-hit'] });
                       if (hits.length !== 1) continue;
                       const t = { x: p.x, y: p.y, props: hits[0].properties };
                       if (t.props.fruitName) return t;   // prefer a revealed fruit
                       fallback = fallback || t;
                     }
                     return fallback;
                   }"""
            )
            if target is None:
                check("ch700/fruit: a hoverable orb on the board", False, "no hit at point")
            else:
                page.mouse.move(target["x"], target["y"])
                page.wait_for_timeout(400)
                text = body_text(page)
                expected = target["props"].get("fruitName")
                if expected:
                    check("ch700/fruit: tooltip carries the revealed fruit line",
                          expected in text, f"hit={target['props']['slug']}")
                else:
                    # The top hit has no revealed fruit — then the tooltip must NOT
                    # invent one (no fruit line at all).
                    check("ch700/fruit: tooltip shows no fruit line for unrevealed",
                          " no Mi" not in text, f"hit={target['props']['slug']}")

            # ---- 5. lens=off empties the presence source
            page.goto(f"{BASE}/?ch=550&lens=off")
            wait_map(page)
            props = presence_props(page)
            check("ch550/off: presence source is empty", len(props) == 0, f"{len(props)} features")

            # ---- 6. haki lens legend: chips only for revealed users
            page.goto(f"{BASE}/?ch=550&lens=haki")
            wait_map(page)
            # Assert structurally: a Conqueror chip exists iff a revealed user is on
            # the board. Chips are <li> rows; the lens descriptor text also names the
            # haki types, so the check is scoped to list items, not the whole page.
            props = presence_props(page)
            has_conq = any("conqueror" in (pr.get("hakiTypes") or "") for pr in props)
            legend = page.locator("text=By haki").count() > 0
            check("ch550/haki: legend heading follows the lens", legend)
            conq_chip = page.locator("li", has_text="Conqueror").count() > 0
            check("ch550/haki: Conqueror chip iff a revealed user is on the board",
                  conq_chip == has_conq, f"chip={conq_chip} users={has_conq}")

            # ---- 7. the populated sea: crews come and GO
            # An organisation with a closed window is not "history" on this chart,
            # it is gone: Baroque Works dissolves at ch. 211 and CP9 does not exist
            # to the reader until Water 7. Both directions are checked, because a
            # forward-only gate would pass while a backward scrub leaked.
            page.goto(f"{BASE}/?ch=200&lens=crew")
            wait_map(page)
            slugs = {pr.get("slug") for pr in presence_props(page)}
            text = body_text(page)
            check("ch200/crew: Baroque Works is charted", "baroque-works" in slugs,
                  f"{len(slugs)} entities on the board")
            check("ch200/crew: CP9 has not been revealed to the reader",
                  "cipher-pol-9" not in slugs and "CP9" not in text)

            page.goto(f"{BASE}/?ch=430&lens=crew")
            wait_map(page)
            slugs = {pr.get("slug") for pr in presence_props(page)}
            check("ch430/crew: CP9 is charted at Enies Lobby", "cipher-pol-9" in slugs)
            check("ch430/crew: Baroque Works is gone (dissolved ch. 211)",
                  "baroque-works" not in slugs)

            # scrub BACK: the window that has not opened yet must un-render
            page.goto(f"{BASE}/?ch=100&lens=crew")
            wait_map(page)
            slugs = {pr.get("slug") for pr in presence_props(page)}
            check("refog ch100/crew: CP9 is not on the board",
                  "cipher-pol-9" not in slugs and "CP9" not in body_text(page))

            # ---- 8. Marines are on the chart, and they are not Warlord grey
            page.goto(f"{BASE}/?ch=560&lens=crew")
            wait_map(page)
            props = presence_props(page)
            by = {pr.get("slug"): pr for pr in props}
            check("ch560/crew: Marineford is crowded", len(props) >= 8, f"{len(props)} entities")
            marines = [s for s in ("sakazuki-akainu", "borsalino-kizaru", "monkey-d-garp",
                                   "sengoku") if s in by]
            check("ch560/crew: the admirals are at Marineford", len(marines) >= 3,
                  f"present: {marines}")
            if marines:
                inks = {by[s]["color"] for s in marines}
                check("ch560/crew: Marines carry the Marine ink, not the Warlord grey",
                      inks == {"#4f7fa8"}, f"inks={inks}")
            # and before Loguetown there is no Navy on this chart at all
            page.goto(f"{BASE}/?ch=50&lens=crew")
            wait_map(page)
            slugs = {pr.get("slug") for pr in presence_props(page)}
            navy = slugs & {"smoker", "monkey-d-garp", "sengoku", "sakazuki-akainu",
                            "borsalino-kizaru", "kuzan-aokiji"}
            check("ch50/crew: no Marine is charted before Loguetown", not navy, f"leaked: {navy}")

            browser.close()
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

    print(f"\n{PASS}/{PASS + FAIL} lens audit checks passed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
