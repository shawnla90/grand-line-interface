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

    finally:
        if server:
            server.terminate()

    print(f"\n{PASS}/{PASS + FAIL} entry audit checks passed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
