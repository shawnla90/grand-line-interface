#!/usr/bin/env python3
"""audit_entries.py — the entry routes' spoiler contract, asserted on the WIRE.

READ-ONLY. urllib, not Playwright, and that is the point: the claim these routes
make is about the SERVER'S BYTES, not about rendered pixels. A browser would
render the same bytes and add flake, a GPU and a paint cycle between us and the
thing being tested. If the name is in the response, the page has already leaked —
whether or not any element ever showed it.

THE ORACLE TEST is the one that matters:

    /island/water-7?ch=100      and      /island/qwertyuiop?ch=100

must be byte-identical. Not "both look uncharted" — identical. A 404 for the
nonexistent slug and a 200 for the fogged one would hand a stranger the entire
future map, one guess at a time, with the fog still perfectly intact.

Requires the dev server: set AUDIT_URL or the script starts its own on
AUDIT_PORT (default 3212).

Run: AUDIT_URL=http://localhost:3000 python3 scripts/audit_entries.py
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("AUDIT_PORT", "3212"))
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


def get(path: str) -> tuple[int, str]:
    """(status, body). A 404 is a RESULT here, not an error — it is the thing
    under test."""
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def absent(name: str, path: str, needles: list[str]) -> None:
    _, html = get(path)
    leaked = [n for n in needles if n in html]
    check(name, not leaked, f"leaked: {leaked}" if leaked else "")


def present(name: str, path: str, needle: str) -> None:
    _, html = get(path)
    check(name, needle in html, "" if needle in html else f"{needle!r} not in response")


def main() -> int:
    server = None
    if "AUDIT_URL" not in os.environ:
        server = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(PORT)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    try:
        for _ in range(60):
            try:
                get("/island/water-7?ch=400")
                break
            except Exception:
                time.sleep(1)
        else:
            print("dev server never came up", file=sys.stderr)
            return 1

        print("\n  the island entry")
        # Water 7 debuts at ch. 323. A chapter-100 reader has not heard of it.
        absent(
            "ch100/water-7: nothing about the island is in the response",
            "/island/water-7?ch=100",
            ["Water 7", "ウォーターセブン", "-73.79", "Water 7 Arc", "voyage order"],
        )
        present("ch400/water-7: it actually reveals", "/island/water-7?ch=400", "Water 7")

        # THE ORACLE. Fogged and nonexistent must be indistinguishable.
        s_fog, fog = get("/island/water-7?ch=100")
        s_non, non = get("/island/qwertyuiop?ch=100")
        check("fogged and nonexistent return the same status",
              s_fog == s_non == 200, f"fogged={s_fog} nonexistent={s_non}")
        # Next injects a build-id/flight payload that differs per route; compare
        # the rendered <main>, which is the whole of what a reader receives.
        def body(html: str) -> str:
            m = re.search(r"<main.*?</main>", html, re.S)
            return m.group(0) if m else html
        h_fog = hashlib.sha256(body(fog).encode()).hexdigest()
        h_non = hashlib.sha256(body(non).encode()).hexdigest()
        check("THE ORACLE: fogged ≡ nonexistent, byte for byte",
              h_fog == h_non, f"{h_fog[:12]} vs {h_non[:12]}")
        check("neither 404s (a 404 IS the oracle)", s_fog == 200 and s_non == 200)
        check("both are noindex", "noindex" in fog and "noindex" in non)
        check("the uncharted body never names what was asked for",
              "water-7" not in body(fog).lower() and "qwertyuiop" not in body(non).lower())

        # An island with no chapter cannot spoil the manga; it charts from ch. 1.
        present("ch1/off-canon island: charted (it has no chapter to fog)",
                "/island/100-island?ch=1", "100% Island")

        # No ?ch at all: ask, never assume.
        _, bare = get("/island/water-7")
        check("no ?ch: asks where you are rather than guessing",
              "Where are you?" in bare and "Water 7" not in bare)

        print("\n  the wanted poster")
        # The nine dropped fields, tested where they would actually hurt. Luffy
        # debuts in chapter 1, so this page is CHARTED — everything below is a
        # field the raw canon row was holding and the poster refused.
        absent(
            "ch1/luffy: charted, and still no future bounty",
            "/character/monkey-d-luffy?ch=1",
            ["3,000,000,000", "3000000000", "1,500,000,000", "30,000,000"],
        )
        absent(
            "ch1/luffy: no devil fruit (the raw row says 'Nika model')",
            "/character/monkey-d-luffy?ch=1",
            ["Nika", "Hito Hito", "Gomu Gomu"],
        )
        absent(
            "ch1/luffy: no epithet — the alias rides the bounty",
            "/character/monkey-d-luffy?ch=1",
            ["Straw Hat Luffy"],
        )
        present("ch1/luffy: says so, honestly", "/character/monkey-d-luffy?ch=1",
                "no bounty posted yet")
        present("ch100/luffy: the first bounty lands", "/character/monkey-d-luffy?ch=100",
                "฿30,000,000")
        present("ch100/luffy: and the alias arrives with it",
                "/character/monkey-d-luffy?ch=100", "Straw Hat Luffy")
        present("ch1053/luffy: the 3B, at last", "/character/monkey-d-luffy?ch=1053",
                "฿3,000,000,000")

        # THE JINBE TRAP, at page level. He debuts 528 and joins 976; his raw
        # canon row says crew_name "Straw Hat Pirates" and job "Helmsman".
        absent(
            "ch600/jinbe: charted, but NOT a Straw Hat for another 376 chapters",
            "/character/jinbe?ch=600",
            ["Straw Hat", "Helmsman"],
        )
        # status: alive|dead is a single present-day value and is dropped.
        absent("ch200/ace: no status — he does not die for 374 chapters",
               "/character/portgas-d-ace?ch=200", ["dead", "deceased"])
        # A character the reader has not met is uncharted, like any fogged thing.
        absent("ch1/katakuri: not met yet", "/character/charlotte-katakuri?ch=1",
               ["Katakuri", "Charlotte"])

        print("\n  crews and fruits: no gate, no page")
        # The AUTHORED window is the gate, and it is exact. The Blackbeard
        # Pirates' first window opens at ch. 223 — Mock Town, Jaya, which is
        # where the reader actually meets them. One chapter earlier they are not
        # on the chart, and no member's debut or crew-table row can vote.
        absent("ch222/blackbeard-pirates: one chapter before the authored window",
               "/crew/blackbeard-pirates?ch=222", ["Blackbeard Pirates"])
        present("ch223/blackbeard-pirates: Mock Town, and there they are",
                "/crew/blackbeard-pirates?ch=223", "Blackbeard Pirates")
        # An ungated crew has no page at all, at any chapter.
        absent("ch1185/an ungated crew is never chartable",
               "/crew/marines?ch=1185", ["Marines"])

        # THE FRUIT_ID TRAP. characters[].fruit_id would list Luffy under the
        # Nika fruit from chapter 1. The reveal table is the only gate.
        absent("ch1100/nika: never chartable — no reveal is authored for it",
               "/fruit/hito-hito-no-mi-nika-model?ch=1100", ["Nika", "Luffy"])
        # Buggy's reveal is chapter 11, and it is exact.
        absent("ch10/bara-bara-no-mi: one chapter early, and it is not there",
               "/fruit/bara-bara-no-mi?ch=10", ["Bara Bara", "Buggy"])
        present("ch11/bara-bara-no-mi: the reveal lands", "/fruit/bara-bara-no-mi?ch=11",
                "Buggy")
        # One fruit, two users across time — the reincarnation case.
        absent("ch200/mera-mera-no-mi: Ace has it; Sabo will not for 544 chapters",
               "/fruit/mera-mera-no-mi?ch=200", ["Sabo"])
        present("ch800/mera-mera-no-mi: and now Sabo does",
                "/fruit/mera-mera-no-mi?ch=800", "Sabo")

        print("\n  the share card")

        def card(path: str) -> tuple[int, bytes]:
            try:
                with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        s_ok, png_charted = card("/api/og/island/water-7?ch=400")
        check("a charted card renders", s_ok == 200 and png_charted[:4] == b"\x89PNG",
              f"status={s_ok} bytes={len(png_charted)}")

        # THE OG ORACLE. A card is the most public surface in the product — it
        # renders in a group chat, a timeline and a crawler's cache, for people
        # who never clicked. A fogged share must preview exactly like a typo.
        _, png_fog = card("/api/og/island/water-7?ch=100")
        _, png_non = card("/api/og/island/qwertyuiop?ch=100")
        h_fog = hashlib.sha256(png_fog).hexdigest()
        h_non = hashlib.sha256(png_non).hexdigest()
        check("THE OG ORACLE: a fogged card is byte-identical to a nonexistent one",
              h_fog == h_non, f"{h_fog[:12]} vs {h_non[:12]}")
        check("and it is NOT the charted card",
              hashlib.sha256(png_charted).hexdigest() != h_fog)

        # The chapter is really in the image, not just in the URL.
        _, png_1000 = card("/api/og/character/monkey-d-luffy?ch=1000")
        _, png_50 = card("/api/og/character/monkey-d-luffy?ch=50")
        check("the card is stamped with the sharer's chapter (1000 != 50)",
              hashlib.sha256(png_1000).hexdigest() != hashlib.sha256(png_50).hexdigest())

        # A garbage family is uncharted, not a 500 — and at the SAME chapter it
        # is the same card, because the footer legitimately stamps the chapter.
        s_bad, png_bad = card("/api/og/nonsense/water-7?ch=100")
        check("a bad family is uncharted, not an error",
              s_bad == 200 and hashlib.sha256(png_bad).hexdigest() == h_fog,
              f"status={s_bad}")

    finally:
        if server:
            server.terminate()

    print(f"\n{PASS}/{PASS + FAIL} entry audit checks passed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
