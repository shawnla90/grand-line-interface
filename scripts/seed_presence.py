#!/usr/bin/env python3
"""seed_presence.py — print a SCAFFOLD for canon/crew_presence.json entries.

Machine proposes, human commits. This script reads the machine-owned mirrors and
prints candidate presence rows to STDOUT ONLY — it never writes a file, and it
imports normalize.py's assert_not_canon defensively so a future edit that tries
to write into canon/ dies loudly.

What it can seed (and what it cannot):
  - crew names/ids from data/raw/crews.json     -> real, but French-dirty
  - ship names from data/raw/boats.json         -> DIRTY (Polar Tang is filed
    under the Kid crew upstream); every ship line carries a _seed_note
  - home-base hints from data/generated/islands.json `affiliation`
    joined to canon/islands.coords.json          -> a hint, not a chapter
  - chapters                                     -> NOTHING upstream has them.
    Every emitted from_chapter is the sentinel 0, which normalize.py REJECTS,
    so a scaffold row cannot reach the artifact until a human types a real
    chapter and a real source_ref.

Usage: python3 scripts/seed_presence.py [crew-name-substring ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import assert_not_canon, load  # noqa: E402  (the boundary, reused)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GEN = ROOT / "data" / "generated"
CANON_DIR = ROOT / "canon"


def main() -> int:
    # Defensive: prove the boundary is armed before doing anything else.
    try:
        assert_not_canon(CANON_DIR / "crew_presence.json")
    except RuntimeError:
        pass  # exactly what we want — the guard fires on canon/ paths
    else:
        raise RuntimeError("assert_not_canon did not fire on a canon/ path — boundary broken")

    crews = load(RAW / "crews.json")
    boats = load(RAW / "boats.json")
    islands = load(GEN / "islands.json")
    coords = {c["slug"]: c for c in load(CANON_DIR / "islands.coords.json")["islands"]}

    wanted = [w.lower() for w in sys.argv[1:]]
    if wanted:
        crews = [c for c in crews if any(w in (c["name"] or "").lower() for w in wanted)]

    ships_by_crew: dict[int, list[dict]] = {}
    for b in boats:
        cid = (b.get("crew") or {}).get("id")
        if cid is not None:
            ships_by_crew.setdefault(cid, []).append(b)

    bases_by_affiliation: dict[str, list[dict]] = {}
    for isl in islands:
        aff = isl.get("affiliation")
        if aff:
            bases_by_affiliation.setdefault(aff.lower(), []).append(isl)

    scaffold = []
    for c in crews:
        name = c["name"]
        ships = ships_by_crew.get(c["id"], [])
        base_hits = []
        for aff, rows in bases_by_affiliation.items():
            probe = name.lower().replace("'s crew", "").replace("the ", "").replace(" crew", "")
            if probe and probe in aff:
                base_hits += [r for r in rows if r["slug"] in coords]
        scaffold.append({
            "slug": "TODO(human): pick the real slug",
            "name": name,
            "crew_id": c["id"],
            "is_yonko": bool(c.get("is_yonko")),
            "vessel": (
                {
                    "name": ships[0]["name"],
                    "slug": "TODO(human)",
                    "_seed_note": "boats.json is DIRTY upstream (the Polar Tang is filed under "
                                  "the Kid crew) — verify every ship name by hand.",
                }
                if ships else None
            ),
            "members": [],
            "windows": [{
                "order": 1,
                "island_slug": base_hits[0]["slug"] if base_hits else None,
                "lng": None,
                "lat": None,
                "label": "TODO(human)",
                "from_chapter": 0,
                "to_chapter": None,
                "source_ref": "Hand-authored. TODO(human): type the real chapter and the real "
                              "reason. The 0 sentinel above is REJECTED by normalize.py on "
                              "purpose — a scaffold row cannot ship.",
                "canon_confidence": "derived" if base_hits else "guess",
                "verified": False,
            }],
            "_seed_note": (
                f"affiliation hint: {[b['slug'] for b in base_hits]}" if base_hits
                else "no island affiliation matched — pick a base or an explicit lng/lat"
            ),
        })

    print(json.dumps({"_scaffold": True, "crews": scaffold}, ensure_ascii=False, indent=2))
    print(f"\n-- {len(scaffold)} scaffold rows. Paste NOTHING without typing real chapters. --",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
