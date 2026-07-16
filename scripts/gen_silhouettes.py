#!/usr/bin/env python3
"""
gen_silhouettes.py — Phase 10B: islands become landmasses. MACHINE-OWNED.

Every mappable manga-canon island gets an ORIGINAL coastline polygon —
deterministic radial-noise blobs seeded from sha256(slug), shaped by what
little the canon tells us (wiki island `type`, archipelago naming, sea) and
sized by narrative weight (voyage waypoints > presence anchors > everywhere
else). No licensed geometry: these are our own marks, MIT like the code.

Same seed -> same coastline, forever: a contributor regenerating the file
gets a byte-identical diff unless the inputs changed.

Inputs   data/generated/islands.json      (type/sea/status/debut)
         canon/islands.coords.json        (positions — the belt model)
         canon/voyage_legs.json           (importance: the Straw Hats' route)
         canon/crew_presence.json         (importance: who anchors where)
         canon/islands.shapes.json        (OPTIONAL hand-drawn overrides:
                                           slug -> GeoJSON geometry. Human wins.)

Output   public/geo/islands.silhouettes.json   (FeatureCollection; properties
         carry slug + debut ONLY — no names, the spoiler contract holds)

Run: python3 scripts/gen_silhouettes.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "data" / "generated"
CANON_DIR = REPO_ROOT / "canon"
OUT_PATH = REPO_ROOT / "public" / "geo" / "islands.silhouettes.json"

POINTS = 56          # vertices per blob — smooth at every zoom the map allows
COORD_DECIMALS = 4   # ~11m; plenty for a stylized chart, keeps the file small


# ---------------------------------------------------------------------------
# Deterministic PRNG — sha256 counter stream, no Python random (seed stability
# across versions is the whole point).
# ---------------------------------------------------------------------------

class Rng:
    def __init__(self, seed: str):
        self.seed = seed.encode()
        self.n = 0

    def unit(self) -> float:
        """[0,1) — 8 hex chars of sha256(seed||counter)."""
        h = hashlib.sha256(self.seed + self.n.to_bytes(4, "big")).hexdigest()
        self.n += 1
        return int(h[:8], 16) / 0xFFFFFFFF

    def range(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.unit()


# ---------------------------------------------------------------------------
# Shape profiles — the little canon we have, made visible
# ---------------------------------------------------------------------------

def profile_for(island: dict) -> dict:
    """Noise profile from island type/name. Amplitudes are fractions of R."""
    t = (island.get("island_type") or "").lower()
    name = island["name"].lower()
    if "archipelago" in name or "islands" in name.split()[-1:]:
        return {"kind": "archipelago"}
    if "sky" in t or island.get("sea") == "Sky":
        # cloud islands: soft, puffy, low-frequency
        return {"kind": "blob", "freqs": [(2, 0.16), (3, 0.10)], "spike": 0.0}
    if "winter" in t:
        # fjords: jagged coast
        return {"kind": "blob", "freqs": [(3, 0.14), (7, 0.12), (11, 0.08)], "spike": 0.06}
    if "summer" in t:
        return {"kind": "blob", "freqs": [(2, 0.14), (5, 0.10)], "spike": 0.0}
    # default temperate coastline
    return {"kind": "blob", "freqs": [(2, 0.13), (4, 0.10), (7, 0.07)], "spike": 0.03}


def blob(rng: Rng, cx: float, cy: float, r_lng: float, r_lat: float, profile: dict) -> list[list[float]]:
    """One closed radial-noise ring around (cx, cy)."""
    freqs = [(f, a) for f, a in profile["freqs"]]
    phases = [rng.range(0, 2 * math.pi) for _ in freqs]
    spike = profile.get("spike", 0.0)
    spike_at = rng.range(0, 2 * math.pi)
    ring: list[list[float]] = []
    for i in range(POINTS):
        th = (i / POINTS) * 2 * math.pi
        f = 1.0
        for (freq, amp), ph in zip(freqs, phases):
            f += amp * math.sin(freq * th + ph)
        if spike:
            # one headland — a cape the eye can hang a bearing on
            d = math.cos(th - spike_at)
            f += spike * max(0.0, d) ** 3
        f = max(0.35, f)
        ring.append([
            round(cx + math.cos(th) * r_lng * f, COORD_DECIMALS),
            round(cy + math.sin(th) * r_lat * f, COORD_DECIMALS),
        ])
    ring.append(ring[0])
    return ring


def geometry_for(island: dict, lng: float, lat: float, radius: float, rng: Rng) -> dict:
    prof = profile_for(island)
    # the Grand Line reads west->east; stretch its islands along the voyage axis
    elong = 1.25 if island.get("sea") == "Grand Line" else rng.range(0.9, 1.15)
    r_lng, r_lat = radius * elong, radius / elong
    if prof["kind"] == "archipelago":
        n = 3 + int(rng.unit() * 3)  # 3-5 islets
        polys = []
        for _ in range(n):
            ox = rng.range(-1.1, 1.1) * r_lng
            oy = rng.range(-0.9, 0.9) * r_lat
            rs = rng.range(0.30, 0.55)
            polys.append([blob(rng, lng + ox, lat + oy, r_lng * rs, r_lat * rs,
                               {"freqs": [(2, 0.14), (5, 0.10)], "spike": 0.0})])
        return {"type": "MultiPolygon", "coordinates": polys}
    return {"type": "Polygon", "coordinates": [blob(rng, lng, lat, r_lng, r_lat, prof)]}


def main() -> int:
    islands = json.loads((GENERATED / "islands.json").read_text())
    coords = json.loads((CANON_DIR / "islands.coords.json").read_text())["islands"]
    voyage = json.loads((CANON_DIR / "voyage_legs.json").read_text())
    presence = json.loads((CANON_DIR / "crew_presence.json").read_text())
    shapes_path = CANON_DIR / "islands.shapes.json"
    overrides: dict = {}
    if shapes_path.exists():
        overrides = json.loads(shapes_path.read_text()).get("shapes", {})

    by_slug = {c["slug"]: c for c in coords}
    voyage_slugs = {w["slug"] for w in voyage["waypoints"] if w.get("slug")}
    anchor_slugs = set()
    for c in presence.get("crews", []) + presence.get("characters", []):
        for w in c.get("windows", []):
            if w.get("island_slug"):
                anchor_slugs.add(w["island_slug"])

    features, skipped = [], 0
    for isl in islands:
        if isl["canon_status"] != "manga" or isl["debut_chapter"] is None:
            continue
        pos = by_slug.get(isl["slug"])
        if not pos:
            skipped += 1
            continue
        slug = isl["slug"]
        rng = Rng(f"silhouette:{slug}")
        # narrative weight -> footprint (degrees). The voyage is the spine of
        # the map; its islands should read as PLACES, not pins.
        if slug in voyage_slugs:
            radius = rng.range(1.40, 1.95)
        elif slug in anchor_slugs:
            radius = rng.range(1.00, 1.45)
        else:
            radius = rng.range(0.50, 0.95)
        geom = overrides.get(slug) or geometry_for(isl, pos["lng"], pos["lat"], radius, rng)
        features.append({
            "type": "Feature",
            # slug + debut only: hovering fog must stay nameless (spoiler contract)
            "properties": {"slug": slug, "debut": isl["debut_chapter"],
                           "hand_drawn": slug in overrides},
            "geometry": geom,
        })

    fc = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/gen_silhouettes.py",
            "license": "Original generated geometry — MIT, same as the code.",
            "note": "Deterministic per-slug: regenerating without input changes is a no-op diff.",
            "islands": len(features),
            "hand_drawn": sum(1 for f in features if f["properties"]["hand_drawn"]),
            "skipped_no_coords": skipped,
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(fc, separators=(",", ":")) + "\n")
    kb = OUT_PATH.stat().st_size // 1024
    print(f"islands.silhouettes.json: {len(features)} landmasses "
          f"({fc['_meta']['hand_drawn']} hand-drawn, {skipped} skipped no-coords), {kb} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
