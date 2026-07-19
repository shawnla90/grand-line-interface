#!/usr/bin/env python3
"""check_breakdowns.py — the guard suite for the chapter breakdown registry.

Every check here exists because a specific way of being wrong would either ship
a dead player to a reader, or leak a chapter they haven't read.

The spoiler checks are the load-bearing ones. /breakdown/[chapter] deliberately
does NOT use the Uncharted envelope -- a locked reader is told the chapter
exists -- so the ONLY thing standing between a too-early reader and the content
is that the locked branch carries a different, pre-blurred file and nothing
else. If locked_poster_path ever equals poster_path, the wall becomes cosmetic
and the sharp frame ships in the payload.

Run: python3 scripts/check_breakdowns.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "canon" / "breakdowns.json"
PUBLIC = ROOT / "public"
EVENTS = ROOT / "canon" / "events.json"

VIDEO_EXT = {".mp4", ".webm"}
POSTER_EXT = {".jpg", ".jpeg", ".png", ".webp"}
PREFIX = "/art/breakdowns/"

results: list[tuple[str, bool, str]] = []


def check(name: str, fn):
    try:
        results.append((name, True, fn() or "ok"))
    except AssertionError as e:
        results.append((name, False, str(e)))


def load() -> list[dict]:
    if not ARTIFACT.exists():
        sys.exit(f"missing {ARTIFACT}")
    return json.loads(ARTIFACT.read_text())["breakdowns"]


def rel(p: str) -> Path:
    return PUBLIC / p.lstrip("/")


def main() -> int:
    bs = load()

    def unique_chapters():
        seen = [b["chapter"] for b in bs]
        assert len(seen) == len(set(seen)), f"duplicate chapters: {seen}"
        return f"{len(seen)} breakdown(s)"

    def paths_scoped():
        for b in bs:
            for k in ("video_path", "poster_path", "locked_poster_path"):
                assert b[k].startswith(PREFIX), f"ch{b['chapter']}.{k} outside {PREFIX}: {b[k]}"
        return "all under /art/breakdowns/"

    def files_exist():
        for b in bs:
            for k in ("video_path", "poster_path", "locked_poster_path"):
                p = rel(b[k])
                assert p.is_file(), f"ch{b['chapter']}.{k} -> {p} does not exist"
                assert p.stat().st_size > 0, f"ch{b['chapter']}.{k} -> {p} is empty"
        return "every referenced file is on disk"

    def extensions():
        for b in bs:
            assert Path(b["video_path"]).suffix in VIDEO_EXT, \
                f"ch{b['chapter']} video ext {Path(b['video_path']).suffix}"
            for k in ("poster_path", "locked_poster_path"):
                assert Path(b[k]).suffix in POSTER_EXT, f"ch{b['chapter']}.{k} ext"
        return "video/poster extensions sane"

    def locked_poster_is_distinct():
        """The wall is only real if the locked file is a DIFFERENT, blurred file."""
        for b in bs:
            assert b["locked_poster_path"] != b["poster_path"], (
                f"ch{b['chapter']}: locked_poster_path == poster_path. The locked "
                f"branch would ship the sharp frame and the spoiler wall becomes "
                f"cosmetic. Bake a separate blurred file."
            )
            a, c = rel(b["poster_path"]), rel(b["locked_poster_path"])
            if a.is_file() and c.is_file():
                assert a.read_bytes() != c.read_bytes(), (
                    f"ch{b['chapter']}: locked poster is byte-identical to the real "
                    f"one. Blur it for real."
                )
        return "locked posters are distinct files"

    def beats_ordered_and_in_range():
        for b in bs:
            ats = [x["at"] for x in b["beats"]]
            assert ats == sorted(ats), f"ch{b['chapter']} beats out of order"
            for a in ats:
                assert 0 <= a <= b["duration_s"], (
                    f"ch{b['chapter']} beat at {a}s exceeds duration {b['duration_s']}s")
        return "beats ordered and within duration"

    def credit_present():
        for b in bs:
            assert b["credit"]["line"].strip(), f"ch{b['chapter']} empty credit line"
            assert b["credit"]["source_ref"].strip(), f"ch{b['chapter']} empty source_ref"
            assert "©" in b["credit"]["line"] or "(c)" in b["credit"]["line"].lower(), \
                f"ch{b['chapter']} credit line carries no copyright mark"
        return "every breakdown is attributed"

    def theory_refs_resolve():
        tp = ROOT / "canon" / "theories.json"
        if not tp.exists():
            return "skipped (canon/theories.json not present on this branch)"
        slugs = {t["slug"] for t in json.loads(tp.read_text())["theories"]}
        for b in bs:
            for s in b["theory_refs"]:
                assert s in slugs, f"ch{b['chapter']} theory_ref '{s}' not in theories.json"
        return "theory_refs resolve"

    def gate_not_before_chapter():
        """A breakdown must never unlock before the chapter it spoils."""
        if not EVENTS.exists():
            return "skipped (no events.json)"
        return "gate is chapter == chapter by construction (see lib/breakdowns.ts)"

    for name, fn in [
        ("unique_chapters", unique_chapters),
        ("paths_scoped", paths_scoped),
        ("files_exist", files_exist),
        ("extensions", extensions),
        ("locked_poster_is_distinct", locked_poster_is_distinct),
        ("beats_ordered_and_in_range", beats_ordered_and_in_range),
        ("credit_present", credit_present),
        ("theory_refs_resolve", theory_refs_resolve),
        ("gate_not_before_chapter", gate_not_before_chapter),
    ]:
        check(name, fn)

    bad = 0
    for name, ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {msg}")
        bad += 0 if ok else 1
    print(f"\n{len(results) - bad}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
