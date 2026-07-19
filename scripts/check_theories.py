#!/usr/bin/env python3
"""check_theories.py — the guard suite for canon/theories.json.

These are assertions about the DATA, run on the hand-authored file the app
loads directly (lib/theories-load.ts). Every one exists because a specific way
of being wrong is a SPOILER, and a spoiler here reaches readers who trusted
the iceberg to keep their place:

  - a theory surfacing before its first evidence renders an empty trail;
  - a title noun the reader hasn't met is a leak the schema can't see, but a
    surfacing chapter EARLIER than the first evidence is the machine-checkable
    half of that authoring rule, so it is enforced;
  - a related slug that doesn't resolve renders a dead link with a name in it;
  - an out-of-range chapter gates a theory into (or out of) existence forever.

Run: python3 scripts/check_theories.py
Exit 0 = the file is shippable. Exit 1 = it is not, and the test that fired says why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEORIES_JSON = ROOT / "canon" / "theories.json"
PONEGLYPHS_JSON = ROOT / "canon" / "poneglyphs.json"
CANON_JSON = ROOT / "data" / "canon.json"
CHAPTERS_RAW = ROOT / "data" / "raw" / "chapters.json"
REPLACEMENT_CHAR = chr(0xFFFD)

STATUS_ENUM = {"open", "partly_confirmed", "confirmed", "debunked"}
CONFIDENCE_ENUM = {"canon", "derived", "guess"}
TIERS = {1, 2, 3, 4, 5}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    text = THEORIES_JSON.read_text(encoding="utf-8")
    check("no_replacement_chars", REPLACEMENT_CHAR not in text,
          "U+FFFD found — a mojibake'd theory is an unverifiable theory")

    data = json.loads(text)
    theories = data.get("theories", [])
    check("has_theories", len(theories) > 0, "theories[] is empty")

    chapters = json.loads(CHAPTERS_RAW.read_text(encoding="utf-8"))
    chapter_max = max(c["id"] for c in chapters)
    canon = json.loads(CANON_JSON.read_text(encoding="utf-8"))
    char_slugs = {c["slug"] for c in canon["characters"]}
    island_slugs = {i["slug"] for i in canon["islands"]}
    poneglyphs = json.loads(PONEGLYPHS_JSON.read_text(encoding="utf-8"))
    poneglyph_slugs = {p["slug"] for p in poneglyphs["poneglyphs"]}

    slugs: set[str] = set()
    for t in theories:
        slug = t.get("slug", "<missing>")
        tag = f"theory[{slug}]"

        check(f"{tag}.slug_unique", slug not in slugs, "duplicate slug")
        slugs.add(slug)

        check(f"{tag}.tier", t.get("tier") in TIERS, f"tier={t.get('tier')} not in 1..5")
        check(f"{tag}.confidence", t.get("canon_confidence") in CONFIDENCE_ENUM,
              f"canon_confidence={t.get('canon_confidence')}")

        surfaces = t.get("surfaces_at_chapter", 0)
        check(f"{tag}.surfaces_in_range", 1 <= surfaces <= chapter_max,
              f"surfaces_at_chapter={surfaces}, corpus max is {chapter_max}")

        ev = t.get("evidence", [])
        check(f"{tag}.has_evidence", len(ev) > 0, "a theory with no evidence is a vibe")
        ev_chapters = [e.get("chapter", 0) for e in ev]
        check(f"{tag}.evidence_ascending", ev_chapters == sorted(ev_chapters),
              f"evidence chapters out of order: {ev_chapters}")
        check(f"{tag}.evidence_in_range",
              all(1 <= c <= chapter_max for c in ev_chapters),
              f"evidence chapter out of 1..{chapter_max}: {ev_chapters}")
        if ev_chapters:
            check(f"{tag}.surfaces_after_first_evidence", surfaces >= ev_chapters[0],
                  f"surfaces at {surfaces} but first evidence is ch. {ev_chapters[0]} — "
                  "a theory must never surface with an empty trail")
        for e in ev:
            ech = e.get("chapter")
            check(f"{tag}.ev{ech}.confidence", e.get("canon_confidence") in CONFIDENCE_ENUM,
                  f"canon_confidence={e.get('canon_confidence')}")
            if e.get("verified") is False:
                check(f"{tag}.ev{ech}.unverified_says_so",
                      "NEEDS HUMAN VERIFICATION" in e.get("source_ref", ""),
                      "verified:false but source_ref doesn't say NEEDS HUMAN VERIFICATION")

        tl = t.get("status_timeline", [])
        check(f"{tag}.has_status", len(tl) > 0, "status_timeline is empty")
        tl_chapters = [w.get("from_chapter", 0) for w in tl]
        check(f"{tag}.status_ascending", tl_chapters == sorted(tl_chapters),
              f"status windows out of order: {tl_chapters}")
        check(f"{tag}.status_enum", all(w.get("status") in STATUS_ENUM for w in tl),
              f"unknown status in {[w.get('status') for w in tl]}")
        if tl_chapters:
            check(f"{tag}.status_covers_surfacing", tl_chapters[0] <= surfaces,
                  f"first status window opens at {tl_chapters[0]} but the theory surfaces "
                  f"at {surfaces} — a surfaced theory must always have a status")
        check(f"{tag}.status_in_range",
              all(1 <= c <= chapter_max for c in tl_chapters),
              f"status window chapter out of 1..{chapter_max}: {tl_chapters}")

        rel = t.get("related", {})
        for s in rel.get("characters", []):
            check(f"{tag}.related_character[{s}]", s in char_slugs,
                  "does not resolve against data/canon.json characters[]")
        for s in rel.get("islands", []):
            check(f"{tag}.related_island[{s}]", s in island_slugs,
                  "does not resolve against data/canon.json islands[]")
        for s in rel.get("poneglyphs", []):
            check(f"{tag}.related_poneglyph[{s}]", s in poneglyph_slugs,
                  "does not resolve against canon/poneglyphs.json")

        check(f"{tag}.unverified", t.get("verified") is False or t.get("verified") is True,
              "verified must be a boolean")

    failed = [(n, d) for (n, ok, d) in results if not ok]
    passed = len(results) - len(failed)
    for n, d in failed:
        print(f"FAIL {n}: {d}")
    print(f"{passed}/{len(results)} checks passed on {len(theories)} theories.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
