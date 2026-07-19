#!/usr/bin/env python3
"""check_overlays.py — the guard suite for canon/overlays.json.

An empty registry passes: the shape ships before the content. Once rows land,
each exists because a specific way of being wrong is a spoiler or a lie:

  - an event_slug that doesn't resolve pins art to a beat that isn't charted;
  - from_chapter earlier than the event's occurred_chapter shows the panel
    before the beat — the one leak the whole design exists to prevent;
  - a media_path with no file behind it renders a broken frame on a page
    that promised the page itself;
  - media outside /art/overlays/ escapes the license boundary public/art
    documents.

Run: python3 scripts/check_overlays.py
Exit 0 = shippable. Exit 1 = not, and the test that fired says why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAYS_JSON = ROOT / "canon" / "overlays.json"
EVENTS_JSON = ROOT / "canon" / "events.json"
CHAPTERS_RAW = ROOT / "data" / "raw" / "chapters.json"
PUBLIC = ROOT / "public"
REPLACEMENT_CHAR = chr(0xFFFD)

KIND_ENUM = {"panel", "animation"}
CONFIDENCE_ENUM = {"canon", "derived", "guess"}
PANEL_EXT = {".png", ".webp", ".jpg", ".jpeg"}
ANIMATION_EXT = {".webm", ".mp4"}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    text = OVERLAYS_JSON.read_text(encoding="utf-8")
    check("no_replacement_chars", REPLACEMENT_CHAR not in text, "U+FFFD found")

    data = json.loads(text)
    overlays = data.get("overlays", [])
    # Empty is a valid, shippable state — the registry precedes the drops.

    chapters = json.loads(CHAPTERS_RAW.read_text(encoding="utf-8"))
    chapter_max = max(c["id"] for c in chapters)
    events = {e["slug"]: e for e in json.loads(EVENTS_JSON.read_text(encoding="utf-8"))["events"]}

    seen: set[str] = set()
    for o in overlays:
        slug = o.get("slug", "<missing>")
        tag = f"overlay[{slug}]"

        check(f"{tag}.unique", slug not in seen, "duplicate slug")
        seen.add(slug)
        check(f"{tag}.kind", o.get("kind") in KIND_ENUM, f"kind={o.get('kind')}")
        check(f"{tag}.confidence", o.get("canon_confidence") in CONFIDENCE_ENUM,
              f"canon_confidence={o.get('canon_confidence')}")

        ev = events.get(o.get("event_slug", ""))
        check(f"{tag}.event_resolves", ev is not None,
              f"event_slug '{o.get('event_slug')}' not in canon/events.json")

        gate = o.get("from_chapter", 0)
        check(f"{tag}.gate_in_range", 1 <= gate <= chapter_max,
              f"from_chapter={gate}, corpus max {chapter_max}")
        if ev is not None:
            check(f"{tag}.gate_after_event", gate >= ev["occurred_chapter"],
                  f"from_chapter {gate} < event occurred_chapter {ev['occurred_chapter']} — "
                  "the panel would show before the beat")

        path = o.get("media_path", "")
        check(f"{tag}.path_in_boundary", path.startswith("/art/overlays/"),
              f"media_path '{path}' escapes /art/overlays/")
        f = PUBLIC / path.lstrip("/")
        check(f"{tag}.media_exists", f.is_file(), f"no file at public{path}")
        ext = Path(path).suffix.lower()
        want = PANEL_EXT if o.get("kind") == "panel" else ANIMATION_EXT
        check(f"{tag}.media_ext", ext in want,
              f"'{ext}' is not a {o.get('kind')} extension {sorted(want)}")

        credit = o.get("credit", {})
        check(f"{tag}.has_credit",
              bool(credit.get("source_ref")) and bool(credit.get("license_note")),
              "credit.source_ref and credit.license_note are both required — "
              "unattributed art does not ship")
        if o.get("verified") is False:
            check(f"{tag}.unverified_says_so",
                  "NEEDS HUMAN VERIFICATION" in credit.get("source_ref", ""),
                  "verified:false but credit.source_ref doesn't say NEEDS HUMAN VERIFICATION")

    failed = [(n, d) for (n, ok, d) in results if not ok]
    passed = len(results) - len(failed)
    for n, d in failed:
        print(f"FAIL {n}: {d}")
    print(f"{passed}/{len(results)} checks passed on {len(overlays)} overlays.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
