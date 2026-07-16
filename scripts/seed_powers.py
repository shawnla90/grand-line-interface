#!/usr/bin/env python3
"""seed_powers.py — print SCAFFOLDS for canon/fruit_reveals.json and canon/haki_users.json.

Machine proposes, human commits. This script reads the machine-owned mirrors and
the presence roster, and prints candidate power rows to STDOUT ONLY — it never
writes a file, and it imports normalize.py's assert_not_canon defensively so a
future edit that tries to write into canon/ dies loudly.

What it can seed (and what it cannot):
  - the roster                                   -> canon/crew_presence.json
    members + characters (the only entities a power fact can attach to)
  - fruit name/type hints from data/raw/
    characters.json's embedded fruit join        -> DIRTY (French-translated
    names, missing for ~half the presence roster); every hint is a _seed_note
  - haki                                          -> NOTHING upstream links haki
    to characters at all; every haki row is pure TODO(human)
  - chapters                                      -> NOTHING upstream has reveal
    chapters. Every emitted from_chapter is the sentinel 0, which normalize.py
    REJECTS, so a scaffold row cannot reach the artifact until a human types a
    real chapter and a real source_ref.

Usage: python3 scripts/seed_powers.py [slug-substring ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import assert_not_canon, load  # noqa: E402  (the boundary, reused)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CANON_DIR = ROOT / "canon"

HAKI_TYPES = ["observation", "armament", "conqueror"]


def slugify(name: str) -> str:
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def main() -> int:
    # Defensive: prove the boundary is armed before doing anything else.
    for target in ("fruit_reveals.json", "haki_users.json"):
        try:
            assert_not_canon(CANON_DIR / target)
        except RuntimeError:
            pass  # exactly what we want — the guard fires on canon/ paths
        else:
            raise RuntimeError("assert_not_canon did not fire on a canon/ path — boundary broken")

    presence = load(CANON_DIR / "crew_presence.json")
    raw_chars = load(RAW / "characters.json")
    fruit_by_char_slug = {}
    for ch in raw_chars:
        fruit = ch.get("fruit")
        if fruit:
            fruit_by_char_slug[slugify(ch["name"])] = fruit

    roster = []
    for c in presence["crews"]:
        for m in c.get("members", []):
            roster.append({"slug": m["slug"], "name": m["name"]})
    for c in presence["characters"]:
        roster.append({"slug": c["slug"], "name": c["name"]})

    wanted = [w.lower() for w in sys.argv[1:]]
    if wanted:
        roster = [r for r in roster if any(w in r["slug"] for w in wanted)]

    fruit_rows = []
    haki_rows = []
    for r in roster:
        hint = fruit_by_char_slug.get(r["slug"])
        fruit_rows.append({
            "slug": r["slug"],
            "name": r["name"],
            "fruit_id": hint["id"] if hint else None,
            "fruit_name": "TODO(human)",
            "fruit_type": "TODO(human)",
            "from_chapter": 0,
            "source_ref": "TODO(human): Hand-authored. Cite where the reader learns this fruit.",
            "canon_confidence": "guess",
            "verified": False,
            "_seed_note": (
                f"upstream fruit join: {hint['name']!r} type {hint['type']!r} — "
                "French-dirty, a HINT not a name" if hint
                else "no upstream fruit join — delete this row if they have no fruit"
            ),
        })
        for haki in HAKI_TYPES:
            haki_rows.append({
                "slug": r["slug"],
                "name": r["name"],
                "haki": haki,
                "from_chapter": 0,
                "source_ref": "TODO(human): Hand-authored. Cite where this haki is revealed.",
                "canon_confidence": "guess",
                "verified": False,
                "_seed_note": "no upstream source links haki to characters — delete unfitting rows",
            })

    print("// ---- canon/fruit_reveals.json 'reveals' candidates (scaffold — DO NOT paste as-is)")
    print(json.dumps(fruit_rows, indent=2, ensure_ascii=False))
    print()
    print("// ---- canon/haki_users.json 'users' candidates (scaffold — DO NOT paste as-is)")
    print(json.dumps(haki_rows, indent=2, ensure_ascii=False))
    print()
    print(f"// {len(fruit_rows)} fruit scaffolds + {len(haki_rows)} haki scaffolds. Every "
          "from_chapter is the sentinel 0 (normalize REJECTS it) and every field a human "
          "must confirm says TODO(human).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
