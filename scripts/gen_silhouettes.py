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

from biomes import BIOMES, biome_for

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "data" / "generated"
CANON_DIR = REPO_ROOT / "canon"
OUT_PATH = REPO_ROOT / "public" / "geo" / "islands.silhouettes.json"

POINTS = 56          # vertices per blob — smooth at every zoom the map allows
COORD_DECIMALS = 4   # ~11m; plenty for a stylized chart, keeps the file small

# Hero islands carry deep terrain (gen_terrain.py) and survive the z8.5 dive,
# so their coastlines get more vertices. Extra points draw NOTHING from the
# rng stream — only hero features change when this set grows.
HERO_SLUGS = {
    "punk-hazard", "arabasta-kingdom", "skypiea", "fish-man-island",
    "thriller-bark", "whole-cake-island", "water-7",
    "enies-lobby", "marineford", "impel-down", "drum-island", "zou",
}
HERO_POINTS = 128


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

def profile_for(island: dict, biome: str) -> dict:
    """Noise profile from the RESOLVED biome (biomes.py: override -> wiki type
    -> sea/name heuristics). Amplitudes are fractions of R. Keying off the
    biome instead of the raw wiki type finally gives Skypiea its cloud-puff
    coast — its sea lives only in the coords file, which biome_for consults."""
    name = island["name"].lower()
    if "archipelago" in name or "islands" in name.split()[-1:]:
        return {"kind": "archipelago"}
    # A SHIP, not a coastline. Thriller Bark is the largest vessel ever built
    # and the story stands on it for an arc, so it is an island on this map —
    # but a blob-shaped one is a lie the eye catches instantly. A hull is still
    # star-convex about its centre, so it fits the same machinery: it is just a
    # different f(theta), and gen_terrain can re-derive it like any other.
    if island.get("island_type") == "Ship":
        return {"kind": "hull", "freqs": [], "spike": 0.0}
    if biome == "sky":
        # cloud islands: soft, puffy, low-frequency
        return {"kind": "blob", "freqs": [(2, 0.16), (3, 0.10)], "spike": 0.0}
    if biome == "winter":
        # fjords: jagged coast
        return {"kind": "blob", "freqs": [(3, 0.14), (7, 0.12), (11, 0.08)], "spike": 0.06}
    if biome == "summer":
        return {"kind": "blob", "freqs": [(2, 0.14), (5, 0.10)], "spike": 0.0}
    if biome == "desert":
        # wind-smoothed shore, one long cape (the caravan headland)
        return {"kind": "blob", "freqs": [(2, 0.12), (3, 0.07)], "spike": 0.10}
    if biome == "volcanic":
        # rugged lava coast
        return {"kind": "blob", "freqs": [(3, 0.13), (6, 0.09)], "spike": 0.05}
    if biome == "jungle":
        # river-cut, irregular
        return {"kind": "blob", "freqs": [(2, 0.13), (5, 0.11), (9, 0.06)], "spike": 0.04}
    # default temperate coastline
    return {"kind": "blob", "freqs": [(2, 0.13), (4, 0.10), (7, 0.07)], "spike": 0.03}


def radius_fn(rng: Rng, profile: dict):
    """The radial factor f(theta) for one blob — the SAME draws blob() makes.

    Exposed so gen_terrain.py can re-derive a hero island's exact coastline
    from the same seed and clip terrain sub-shapes inside it with a cheap
    radial test (the rings are star-convex around their center by
    construction). Consumes len(freqs)+1 draws, exactly like blob() did.
    """
    freqs = [(f, a) for f, a in profile["freqs"]]
    phases = [rng.range(0, 2 * math.pi) for _ in freqs]
    spike = profile.get("spike", 0.0)
    spike_at = rng.range(0, 2 * math.pi)

    if profile.get("kind") == "hull":
        # A hull, in polar form. The radius is LARGEST along the keel (theta 0
        # and pi — bow and stern) and squeezed abeam, which is what makes a lens
        # rather than an ellipse; the |sin| exponent is the fineness of the
        # entry. The cos term lets the stern out a little so the thing has a
        # direction. The draws above are consumed either way, so the seed stream
        # stays aligned with every other island's.
        def hull_of(th: float) -> float:
            beam = 1.0 - 0.58 * abs(math.sin(th)) ** 1.5
            return max(0.2, beam * (1.0 - 0.10 * math.cos(th)))

        return hull_of

    def f_of(th: float) -> float:
        f = 1.0
        for (freq, amp), ph in zip(freqs, phases):
            f += amp * math.sin(freq * th + ph)
        if spike:
            # one headland — a cape the eye can hang a bearing on
            d = math.cos(th - spike_at)
            f += spike * max(0.0, d) ** 3
        return max(0.35, f)

    return f_of


def blob(rng: Rng, cx: float, cy: float, r_lng: float, r_lat: float, profile: dict,
         points: int = POINTS) -> list[list[float]]:
    """One closed radial-noise ring around (cx, cy)."""
    f_of = radius_fn(rng, profile)
    ring: list[list[float]] = []
    for i in range(points):
        th = (i / points) * 2 * math.pi
        f = f_of(th)
        ring.append([
            round(cx + math.cos(th) * r_lng * f, COORD_DECIMALS),
            round(cy + math.sin(th) * r_lat * f, COORD_DECIMALS),
        ])
    ring.append(ring[0])
    return ring


def geometry_for(island: dict, biome: str, lng: float, lat: float, radius: float, rng: Rng) -> dict:
    prof = profile_for(island, biome)
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
    points = HERO_POINTS if island["slug"] in HERO_SLUGS else POINTS
    return {"type": "Polygon", "coordinates": [blob(rng, lng, lat, r_lng, r_lat, prof, points)]}


SILHOUETTE_INPUTS = (
    "data/generated/islands.json",
    "canon/islands.extra.json",
    "canon/islands.coords.json",
    "canon/islands.biomes.json",
    "canon/islands.shapes.json",
    "canon/voyage_legs.json",
    "canon/crew_presence.json",
)


def inputs_sha() -> str:
    """sha256 over every input file, in a fixed order. Missing files hash as
    empty — canon/islands.shapes.json is an optional override door."""
    h = hashlib.sha256()
    for rel in SILHOUETTE_INPUTS:
        f = REPO_ROOT / rel
        h.update(rel.encode())
        h.update(f.read_bytes() if f.exists() else b"")
    return h.hexdigest()


def load_islands() -> list[dict]:
    """The generated harvest PLUS the hand-authored extras.

    Both generators and normalize.py must agree on what an island is, or the
    map grows a pin with no coastline under it. The extras exist because the
    wiki files Thriller Bark as a ship — see canon/islands.extra.json.
    """
    islands = json.loads((GENERATED / "islands.json").read_text())
    extra_path = CANON_DIR / "islands.extra.json"
    if extra_path.exists():
        islands = [*islands, *json.loads(extra_path.read_text())["islands"]]
    return islands


def main() -> int:
    islands = load_islands()
    coords = json.loads((CANON_DIR / "islands.coords.json").read_text())["islands"]
    voyage = json.loads((CANON_DIR / "voyage_legs.json").read_text())
    presence = json.loads((CANON_DIR / "crew_presence.json").read_text())
    shapes_path = CANON_DIR / "islands.shapes.json"
    overrides: dict = {}
    if shapes_path.exists():
        overrides = json.loads(shapes_path.read_text()).get("shapes", {})
    biomes_path = CANON_DIR / "islands.biomes.json"
    biome_overrides: dict = {}
    if biomes_path.exists():
        biome_overrides = json.loads(biomes_path.read_text()).get("biomes", {})

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
        biome = biome_for(isl, pos.get("sea"), biome_overrides)
        geom = overrides.get(slug) or geometry_for(isl, biome, pos["lng"], pos["lat"], radius, rng)
        features.append({
            "type": "Feature",
            # slug + debut + biome only: hovering fog must stay nameless
            # (spoiler contract) — biome is a paint key, gated to pixels by the
            # same revealed(ch) opacity as the coastline itself
            "properties": {"slug": slug, "debut": isl["debut_chapter"],
                           "hand_drawn": slug in overrides, "biome": biome},
            "geometry": geom,
        })

    fc = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/gen_silhouettes.py",
            # The fingerprint of every input this run read. check_canon compares
            # it against the files on disk, because this artifact's shape depends
            # on things that do not look like geometry: an island's footprint
            # grows when a crew starts anchoring there, so editing
            # crew_presence.json silently invalidates the coastlines. It did
            # exactly that once, and nothing said so.
            "inputs_sha": inputs_sha(),
            "license": "Original generated geometry — MIT, same as the code.",
            "note": "Deterministic per-slug: regenerating without input changes is a no-op diff.",
            "islands": len(features),
            "hand_drawn": sum(1 for f in features if f["properties"]["hand_drawn"]),
            "skipped_no_coords": skipped,
            # classification drift shows up here as a reviewable diff
            "biomes": {b: sum(1 for f in features if f["properties"]["biome"] == b)
                       for b in sorted(BIOMES)},
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
