#!/usr/bin/env python3
"""verification_queue.py — every hand-authored claim still awaiting a human eye.

The atlas's honesty rule is that a machine-derived fact must not look
human-confirmed. The enforcement half lives in scripts/check_canon.py; this is
the ACCOUNTING half: one re-runnable report that walks every canon/*.json file,
finds every row carrying `verified: false`, and lists them grouped by file so
Shawn (or any contributor) can burn the list down against the manga. The number
at the top is the project's honesty debt. When it reaches zero, the "Verify the
canon" roadmap item is done — not before.

Also summarizes island-position confidence from canon/islands.coords.json,
because positions use canon_confidence (canon/derived/guess), not a verified
flag — same debt, different ledger.

Run: python3 scripts/verification_queue.py
Writes: data/review/verification-queue.md
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "canon"
OUT = ROOT / "data" / "review" / "verification-queue.md"

# Files with no verifiable claims: build provenance and the coords ledger
# (coords carry canon_confidence, summarized separately below).
SKIP = {"build_log.json", "islands.coords.json"}

CHAPTER_KEYS = (
    "join_chapter", "revealed_chapter", "occurred_chapter", "from_chapter",
    "as_of_chapter", "chapter",
)


def label_of(row: dict, crumbs: list[str]) -> str:
    for k in ("name", "label", "slug"):
        v = row.get(k)
        if isinstance(v, str) and v:
            return v
    return " › ".join(c for c in crumbs if c) or "(unnamed row)"


def chapter_of(row: dict) -> str:
    for k in CHAPTER_KEYS:
        v = row.get(k)
        if isinstance(v, int):
            to = row.get("to_chapter")
            return f"ch. {v}–{to}" if isinstance(to, int) else f"ch. {v}"
    return "—"


def walk(node, crumbs: list[str], found: list[dict]) -> None:
    """Collect every dict that carries a `verified` key, wherever it nests."""
    if isinstance(node, dict):
        if "verified" in node:
            found.append({
                "label": label_of(node, crumbs),
                "chapter": chapter_of(node),
                "confidence": node.get("canon_confidence", "—"),
                "verified": bool(node.get("verified")),
            })
        for k, v in node.items():
            if k.startswith("_"):
                continue
            next_crumb = node.get("name") or node.get("slug") or ""
            walk(v, crumbs + [next_crumb] if next_crumb not in crumbs else crumbs, found)
    elif isinstance(node, list):
        for item in node:
            walk(item, crumbs, found)


def main() -> int:
    lines: list[str] = []
    w = lines.append

    per_file: dict[str, list[dict]] = {}
    for path in sorted(CANON.glob("*.json")):
        if path.name in SKIP:
            continue
        found: list[dict] = []
        walk(json.loads(path.read_text()), [], found)
        if found:
            per_file[path.name] = found

    unverified = sum(1 for rows in per_file.values() for r in rows if not r["verified"])
    verified = sum(1 for rows in per_file.values() for r in rows if r["verified"])

    w("# Verification queue — the honesty debt")
    w("")
    w(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `scripts/verification_queue.py`. Re-run any time; this file is a report, not a source._")
    w("")
    w(f"**{unverified} claims awaiting human verification. {verified} verified.**")
    w("")
    w("Every row below is hand-authored in `canon/` with `verified: false` — the UI")
    w("already renders these as unverified. To burn one down: confirm the chapter")
    w("against the manga, flip `verified` to `true` in the named file, and re-run")
    w("`scripts/check_canon.py`. The build log's rule applies: a claim is verified")
    w("when a human checked the page, not when it looks right.")
    w("")

    for fname, rows in per_file.items():
        pending = [r for r in rows if not r["verified"]]
        done = len(rows) - len(pending)
        w(f"## `canon/{fname}` — {len(pending)} pending" + (f", {done} verified" if done else ""))
        w("")
        if not pending:
            w("_All rows verified._")
            w("")
            continue
        w("| Claim | Chapter | Confidence |")
        w("|---|---|---|")
        for r in sorted(pending, key=lambda r: (r["chapter"] == "—", r["chapter"], r["label"])):
            w(f"| {r['label']} | {r['chapter']} | {r['confidence']} |")
        w("")

    # Island positions: same debt, tracked as confidence rather than a flag.
    coords = json.loads((CANON / "islands.coords.json").read_text())
    conf = Counter(
        row.get("canon_confidence", "unknown")
        for row in coords.get("islands", {}).values()
    ) if isinstance(coords.get("islands"), dict) else Counter(
        row.get("canon_confidence", "unknown") for row in coords.get("islands", [])
    )
    w("## `canon/islands.coords.json` — position confidence")
    w("")
    w("Positions carry `canon_confidence`, not a `verified` flag. `derived`/`guess`")
    w("pins render as hollow rings until a human promotes them via `/admin/place`.")
    w("")
    w("| Confidence | Islands |")
    w("|---|---|")
    for k in ("canon", "derived", "guess", "unknown"):
        if conf.get(k):
            w(f"| {k} | {conf[k]} |")
    w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} — {unverified} pending, {verified} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
