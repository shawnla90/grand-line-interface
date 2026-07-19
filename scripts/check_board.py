#!/usr/bin/env python3
"""check_board.py — the guard suite for canon/key_players.json.

Assertions about the DATA, run on the hand-authored file the app loads
directly (lib/board-load.ts). Each exists because a specific way of being
wrong is a spoiler or a lie on the war table:

  - a player slug that doesn't resolve renders a dead card;
  - a position window on an island the reader hasn't charted puts that
    island's NAME in the window label before its debut — the board's active
    window must never open before its island exists;
  - out-of-order windows make presenceWindowAt resolve the wrong "now";
  - overlapping windows make two places true at once.

Run: python3 scripts/check_board.py
Exit 0 = the file is shippable. Exit 1 = it is not, and the test that fired says why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYERS_JSON = ROOT / "canon" / "key_players.json"
CANON_JSON = ROOT / "data" / "canon.json"
CHAPTERS_RAW = ROOT / "data" / "raw" / "chapters.json"
REPLACEMENT_CHAR = chr(0xFFFD)

CONFIDENCE_ENUM = {"canon", "derived", "guess"}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    text = PLAYERS_JSON.read_text(encoding="utf-8")
    check("no_replacement_chars", REPLACEMENT_CHAR not in text,
          "U+FFFD found — a mojibake'd board is an unverifiable board")

    data = json.loads(text)
    players = data.get("players", [])
    check("has_players", len(players) > 0, "players[] is empty")

    chapters = json.loads(CHAPTERS_RAW.read_text(encoding="utf-8"))
    chapter_max = max(c["id"] for c in chapters)
    canon = json.loads(CANON_JSON.read_text(encoding="utf-8"))
    characters = {}
    for c in canon["characters"]:
        cur = characters.get(c["slug"])
        if cur is None or c["id"] < cur["id"]:
            characters[c["slug"]] = c
    islands = {i["slug"]: i for i in canon["islands"]}

    slugs: set[str] = set()
    for p in players:
        slug = p.get("slug", "<missing>")
        tag = f"player[{slug}]"

        check(f"{tag}.slug_unique", slug not in slugs, "duplicate slug")
        slugs.add(slug)

        row = characters.get(slug)
        check(f"{tag}.resolves", row is not None,
              "does not resolve against data/canon.json characters[]")
        debut = row.get("debut_chapter") if row else None
        check(f"{tag}.has_debut", debut is not None,
              "character has null debut_chapter — the board's name gate can never pass, "
              "the card is permanently dark (the lib/entry.ts rule)")

        tl = p.get("position_timeline", [])
        check(f"{tag}.has_positions", len(tl) > 0, "position_timeline is empty")
        froms = [w.get("from_chapter", 0) for w in tl]
        check(f"{tag}.positions_ascending", froms == sorted(froms),
              f"windows out of order: {froms}")
        check(f"{tag}.positions_in_range",
              all(1 <= f <= chapter_max for f in froms),
              f"window chapter out of 1..{chapter_max}: {froms}")
        if debut is not None and froms:
            check(f"{tag}.first_window_after_debut", froms[0] >= debut,
                  f"first window opens ch. {froms[0]} but the character debuts ch. {debut}")

        prev_to = None
        for w in tl:
            f, t = w.get("from_chapter"), w.get("to_chapter")
            wtag = f"{tag}.window[{f}]"
            if t is not None:
                check(f"{wtag}.span", t >= f, f"to_chapter {t} < from_chapter {f}")
            if prev_to is not None:
                check(f"{wtag}.no_overlap", f > prev_to,
                      f"opens ch. {f} inside the previous window (closes {prev_to})")
            prev_to = t if t is not None else chapter_max
            check(f"{wtag}.confidence", w.get("canon_confidence") in CONFIDENCE_ENUM,
                  f"canon_confidence={w.get('canon_confidence')}")
            if w.get("verified") is False:
                check(f"{wtag}.unverified_says_so",
                      "NEEDS HUMAN VERIFICATION" in w.get("source_ref", ""),
                      "verified:false but source_ref doesn't say NEEDS HUMAN VERIFICATION")
            isl = w.get("island_slug")
            if isl is not None:
                island = islands.get(isl)
                check(f"{wtag}.island_resolves", island is not None,
                      f"island_slug '{isl}' not in data/canon.json islands[]")
                if island is not None and island.get("debut_chapter") is not None:
                    check(f"{wtag}.island_debuted", f >= island["debut_chapter"],
                          f"window opens ch. {f} but {isl} debuts ch. {island['debut_chapter']} — "
                          "an active window would name an uncharted island")

        forms = p.get("form_timeline", [])
        ffroms = [f.get("from_chapter", 0) for f in forms]
        check(f"{tag}.forms_ascending", ffroms == sorted(ffroms),
              f"form windows out of order: {ffroms}")
        check(f"{tag}.forms_in_range",
              all(1 <= f <= chapter_max for f in ffroms),
              f"form chapter out of 1..{chapter_max}: {ffroms}")
        for f in forms:
            if f.get("verified") is False:
                check(f"{tag}.form[{f.get('from_chapter')}].unverified_says_so",
                      "NEEDS HUMAN VERIFICATION" in f.get("source_ref", ""),
                      "verified:false but source_ref doesn't say NEEDS HUMAN VERIFICATION")

    failed = [(n, d) for (n, ok, d) in results if not ok]
    passed = len(results) - len(failed)
    for n, d in failed:
        print(f"FAIL {n}: {d}")
    print(f"{passed}/{len(results)} checks passed on {len(players)} players.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
