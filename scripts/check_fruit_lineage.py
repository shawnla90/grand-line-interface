#!/usr/bin/env python3
"""check_fruit_lineage.py — the guard suite for canon/fruit_lineage.json.

Assertions about the DATA. Each exists because a specific way of being wrong
is a spoiler:

  - a lineage whose fruit_slug has no authored reveal would hang a story on a
    fruit the app can never chart (and its gate would never open);
  - a lineage event EARLIER than the fruit's earliest reveal would be reachable
    the moment the fruit surfaces — fine — but an event earlier than chapter 1
    or later than the corpus is a typo that gates content into or out of
    existence forever;
  - out-of-order events render a scrambled chain.

Run: python3 scripts/check_fruit_lineage.py
Exit 0 = shippable. Exit 1 = not, and the test that fired says why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINEAGE_JSON = ROOT / "canon" / "fruit_lineage.json"
REVEALS_JSON = ROOT / "canon" / "fruit_reveals.json"
CHAPTERS_RAW = ROOT / "data" / "raw" / "chapters.json"
REPLACEMENT_CHAR = chr(0xFFFD)

KIND_ENUM = {"revealed", "inherited", "taken", "staked", "lore"}
CONFIDENCE_ENUM = {"canon", "derived", "guess"}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    text = LINEAGE_JSON.read_text(encoding="utf-8")
    check("no_replacement_chars", REPLACEMENT_CHAR not in text, "U+FFFD found")

    data = json.loads(text)
    lineages = data.get("lineages", [])
    check("has_lineages", len(lineages) > 0, "lineages[] is empty")

    chapters = json.loads(CHAPTERS_RAW.read_text(encoding="utf-8"))
    chapter_max = max(c["id"] for c in chapters)
    reveals = json.loads(REVEALS_JSON.read_text(encoding="utf-8"))["reveals"]
    reveal_chapters: dict[str, int] = {}
    for r in reveals:
        s = r["fruit_slug"]
        reveal_chapters[s] = min(reveal_chapters.get(s, 10**9), r["from_chapter"])

    seen: set[str] = set()
    for l in lineages:
        slug = l.get("fruit_slug", "<missing>")
        tag = f"lineage[{slug}]"

        check(f"{tag}.unique", slug not in seen, "duplicate fruit_slug")
        seen.add(slug)
        check(f"{tag}.fruit_revealed", slug in reveal_chapters,
              "fruit_slug has no row in canon/fruit_reveals.json — the lineage could never render")

        ev = l.get("events", [])
        check(f"{tag}.has_events", len(ev) > 0, "events[] is empty")
        chs = [e.get("chapter", 0) for e in ev]
        check(f"{tag}.events_ascending", chs == sorted(chs), f"events out of order: {chs}")
        check(f"{tag}.events_in_range", all(1 <= c <= chapter_max for c in chs),
              f"event chapter out of 1..{chapter_max}: {chs}")
        for e in ev:
            ech = e.get("chapter")
            check(f"{tag}.ev{ech}.kind", e.get("kind") in KIND_ENUM, f"kind={e.get('kind')}")
            check(f"{tag}.ev{ech}.confidence",
                  e.get("canon_confidence") in CONFIDENCE_ENUM,
                  f"canon_confidence={e.get('canon_confidence')}")
            if e.get("verified") is False:
                check(f"{tag}.ev{ech}.unverified_says_so",
                      "NEEDS HUMAN VERIFICATION" in e.get("source_ref", ""),
                      "verified:false but source_ref doesn't say NEEDS HUMAN VERIFICATION")

    failed = [(n, d) for (n, ok, d) in results if not ok]
    passed = len(results) - len(failed)
    for n, d in failed:
        print(f"FAIL {n}: {d}")
    print(f"{passed}/{len(results)} checks passed on {len(lineages)} lineages.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
