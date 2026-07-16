#!/usr/bin/env python3
"""
gen_terrain.py — Landfall: hero islands become real places. MACHINE-OWNED.

Deep-zoom terrain for the hero islands as ORIGINAL vector geometry — pure
generated fills and lines, MIT like the code (no rasters, no licensed art,
no AI gen). Punk Hazard splits into a burning half and a frozen half with
volcano cones; Arabasta gets dune bands and one meandering river; Skypiea
gets stacked cloud terraces and wisp swirls.

THE CLIPPING TRICK: gen_silhouettes' coastline rings are star-convex around
their center — the radial factor f(theta) is re-derivable from the same
sha256 seed (radius_fn). Every terrain shape here is built in polar
coordinates as a FRACTION of f(theta), so it sits exactly inside its
island's coastline with no polygon-clipping dependency.

SPOILER CONTRACT: every feature carries {slug, debut, kind, sort}. Debut
gates the pixels in WorldMap's paint() with the same revealed(ch) case as
the silhouettes — a fogged hero island never shows a single ember.

Inputs   data/generated/islands.json       (debut/type/sea/status)
         canon/islands.coords.json         (positions + the real sea)
         canon/islands.biomes.json         (biome overrides)
         canon/voyage_legs.json            (footprint weight — must match
         canon/crew_presence.json           gen_silhouettes exactly)

Output   public/geo/islands.terrain.json   (FeatureCollection)

Run: python3 scripts/gen_terrain.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from biomes import biome_for
from gen_silhouettes import COORD_DECIMALS, HERO_SLUGS, Rng, profile_for, radius_fn

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "data" / "generated"
CANON_DIR = REPO_ROOT / "canon"
OUT_PATH = REPO_ROOT / "public" / "geo" / "islands.terrain.json"

TAU = 2 * math.pi


class HeroRing:
    """A hero island's exact coastline, re-derived from the silhouette seed."""

    def __init__(self, isl: dict, pos: dict, biome: str,
                 voyage_slugs: set, anchor_slugs: set):
        slug = isl["slug"]
        rng = Rng(f"silhouette:{slug}")
        # EXACT draw order of gen_silhouettes.main() + geometry_for():
        if slug in voyage_slugs:
            radius = rng.range(1.40, 1.95)
        elif slug in anchor_slugs:
            radius = rng.range(1.00, 1.45)
        else:
            radius = rng.range(0.50, 0.95)
        prof = profile_for(isl, biome)
        assert prof["kind"] != "archipelago", f"{slug}: hero terrain needs a single ring"
        elong = 1.25 if isl.get("sea") == "Grand Line" else rng.range(0.9, 1.15)
        self.cx, self.cy = pos["lng"], pos["lat"]
        self.r_lng, self.r_lat = radius * elong, radius / elong
        self.f = radius_fn(rng, prof)

    def pt(self, th: float, t: float = 1.0) -> list[float]:
        """The point at angle th, at fraction t of the coastline radius."""
        f = self.f(th) * t
        return [round(self.cx + math.cos(th) * self.r_lng * f, COORD_DECIMALS),
                round(self.cy + math.sin(th) * self.r_lat * f, COORD_DECIMALS)]

    def arc(self, th0: float, th1: float, t: float, n: int = 72) -> list[list[float]]:
        return [self.pt(th0 + (th1 - th0) * i / n, t) for i in range(n + 1)]

    def ring(self, t: float, n: int = 128, wobble: float = 0.0, wobble_freq: int = 3,
             wobble_phase: float = 0.0) -> list[list[float]]:
        """A closed ring at fraction t of the coast, optionally re-noised."""
        out = []
        for i in range(n):
            th = (i / n) * TAU
            tt = t * (1.0 + wobble * math.sin(wobble_freq * th + wobble_phase))
            out.append(self.pt(th, tt))
        out.append(out[0])
        return out

    def small_blob(self, rng: Rng, th: float, t: float, size: float,
                   n: int = 40) -> list[list[float]]:
        """A little closed blob centered at (th, t), sized as a fraction of R."""
        c = self.pt(th, t)
        phases = [rng.range(0, TAU) for _ in range(2)]
        out = []
        for i in range(n):
            a = (i / n) * TAU
            f = 1.0 + 0.18 * math.sin(2 * a + phases[0]) + 0.10 * math.sin(5 * a + phases[1])
            out.append([round(c[0] + math.cos(a) * self.r_lng * size * f, COORD_DECIMALS),
                        round(c[1] + math.sin(a) * self.r_lat * size * f, COORD_DECIMALS)])
        out.append(out[0])
        return out


def feat(slug: str, debut: int, kind: str, sort: int, geom: dict) -> dict:
    return {"type": "Feature",
            "properties": {"slug": slug, "debut": debut, "kind": kind, "sort": sort},
            "geometry": geom}


def poly(*rings: list[list[float]]) -> dict:
    return {"type": "Polygon", "coordinates": list(rings)}


def line(pts: list[list[float]]) -> dict:
    return {"type": "LineString", "coordinates": pts}


# ---------------------------------------------------------------------------
# Punk Hazard — the island the war cut in half: fire on one side, ice on the
# other, a scorched boundary between them.
# ---------------------------------------------------------------------------

def punk_hazard(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    split = rng.range(0, TAU)  # the dividing meridian's angle
    out: list[dict] = []

    # the two half-grounds: coast arc (inset) + fan back through the center
    center = [round(ring.cx, COORD_DECIMALS), round(ring.cy, COORD_DECIMALS)]
    fire_arc = ring.arc(split, split + math.pi, 0.96)
    out.append(feat(slug, debut, "fire-ground", 1, poly(fire_arc + [center, fire_arc[0]])))
    ice_arc = ring.arc(split + math.pi, split + TAU, 0.96)
    out.append(feat(slug, debut, "ice-ground", 1, poly(ice_arc + [center, ice_arc[0]])))

    # the scorched boundary strip along the diameter
    w = 0.05
    a, b = split, split + math.pi
    strip = [ring.pt(a, 0.97), ring.pt(a + w, 0.5), ring.pt(a + w, 0.12),
             ring.pt(b - w, 0.12), ring.pt(b - w, 0.5), ring.pt(b, 0.97),
             ring.pt(b + w, 0.5), ring.pt(b + w, 0.12),
             ring.pt(a - w + TAU, 0.12), ring.pt(a - w + TAU, 0.5)]
    strip.append(strip[0])
    out.append(feat(slug, debut, "boundary", 2, poly(strip)))

    # three volcano cones on the burning side, craters on top
    for i, frac in enumerate((0.25, 0.52, 0.78)):
        th = split + math.pi * frac
        t = rng.range(0.38, 0.58)
        size = rng.range(0.11, 0.16)
        cone_rng = Rng(f"terrain:{slug}:volcano{i}")
        out.append(feat(slug, debut, "volcano", 3,
                        poly(ring.small_blob(cone_rng, th, t, size))))
        out.append(feat(slug, debut, "crater", 4,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:crater{i}"), th, t, size * 0.38))))
        # an ember rim around each cone
        out.append(feat(slug, debut, "fire-glow", 0,
                        line(ring.small_blob(Rng(f"terrain:{slug}:glow{i}"), th, t, size * 1.25))))

    # the burning coast itself glows
    out.append(feat(slug, debut, "fire-glow", 0, line(ring.arc(split, split + math.pi, 0.985, 96))))

    # crevasses cracking the frozen side
    for i, frac in enumerate((0.28, 0.55, 0.8)):
        th0 = split + math.pi + math.pi * frac
        crev_rng = Rng(f"terrain:{slug}:crevasse{i}")
        pts = []
        steps = 9
        for s in range(steps + 1):
            t = 0.18 + (0.72 - 0.18) * s / steps
            jag = crev_rng.range(-0.055, 0.055)
            pts.append(ring.pt(th0 + jag, t))
        out.append(feat(slug, debut, "crevasse", 5, line(pts)))
    return out


# ---------------------------------------------------------------------------
# Arabasta — the desert kingdom: dune bands sweeping inland, one river
# (the Sandora) meandering from the coast, a green delta at its mouth.
# ---------------------------------------------------------------------------

def arabasta(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []

    # concentric dune bands (outer ring + inner hole => no translucent stacking)
    fracs = [0.92, 0.76, 0.60, 0.44, 0.28, 0.14]
    for i in range(len(fracs) - 1):
        ph = rng.range(0, TAU)
        outer = ring.ring(fracs[i], wobble=0.045, wobble_freq=3 + (i % 2), wobble_phase=ph)
        inner = ring.ring(fracs[i + 1], wobble=0.045, wobble_freq=3 + ((i + 1) % 2), wobble_phase=ph)
        kind = "dune-a" if i % 2 == 0 else "dune-b"
        # GeoJSON hole: reverse the inner ring's winding
        out.append(feat(slug, debut, kind, 1 + i, poly(outer, inner[::-1])))
    # the innermost heart is a plain disk
    out.append(feat(slug, debut, "dune-a", 1 + len(fracs),
                    poly(ring.ring(fracs[-1], wobble=0.045, wobble_freq=4,
                                   wobble_phase=rng.range(0, TAU)))))

    # the river: from the coast, meandering toward the interior
    mouth = rng.range(0, TAU)
    steps = 14
    river = []
    for s in range(steps + 1):
        t = 0.97 - (0.97 - 0.18) * s / steps
        wiggle = 0.10 * math.sin(s * 1.15) * (1 - s / steps + 0.3)
        river.append(ring.pt(mouth + wiggle, t))
    out.append(feat(slug, debut, "riverbank", 8, line(river)))
    out.append(feat(slug, debut, "river", 9, line(river)))

    # the delta: a green patch where the river meets the sea
    out.append(feat(slug, debut, "delta", 10,
                    poly(ring.small_blob(Rng(f"terrain:{slug}:delta"), mouth, 0.92, 0.10))))
    return out


# ---------------------------------------------------------------------------
# Skypiea — the island in the sky: stacked cloud terraces rising toward the
# center (brighter = higher), wisps of the Milky Road swirling off them.
# ---------------------------------------------------------------------------

# The 2.5D ascent's sea-level furniture. MUST match components/skypiea.ts.
SKY_BASE = (-91.1362, 8.2)


def skypiea(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    tiers = [(0.85, "cloud-puff-a", 1), (0.55, "cloud-puff-b", 2), (0.30, "cloud-puff-c", 3)]
    for t, kind, sort in tiers:
        ph = rng.range(0, TAU)
        out.append(feat(slug, debut, kind, sort,
                        poly(ring.ring(t, wobble=0.08, wobble_freq=5, wobble_phase=ph))))
    # wisp swirls — arcs spiraling outward
    for i in range(3):
        th0 = rng.range(0, TAU)
        sweep = rng.range(1.6, 2.6)
        pts = []
        steps = 24
        for s in range(steps + 1):
            th = th0 + sweep * s / steps
            t = 0.25 + (0.88 - 0.25) * s / steps
            pts.append(ring.pt(th, t))
        out.append(feat(slug, debut, "cloud-wisp", 4, line(pts)))

    # THE FLOAT ILLUSION: the island's own outline, shrunk and dropped onto the
    # sea at the Knock-Up Stream's base, reads as the shadow it casts from
    # above. Same seed => the shadow visibly matches the island's shape.
    dx, dy = SKY_BASE[0] - ring.cx, SKY_BASE[1] - ring.cy
    for scale, kind in ((0.63, "sky-shadow-soft"), (0.55, "sky-shadow-core")):
        shadow = [[round(x + dx, COORD_DECIMALS), round(y + dy, COORD_DECIMALS)]
                  for x, y in ring.ring(scale, wobble=0.04, wobble_freq=4,
                                        wobble_phase=rng.range(0, TAU))]
        out.append(feat(slug, debut, kind, 0, poly(shadow)))

    # THE KNOCK-UP STREAM: nested trapezoids from the sea base up to the
    # island's southern coast — the fake vertical gradient (inner = brighter).
    south_lat = ring.pt(-TAU / 4, 1.0)[1]
    top_lat = round(south_lat + 0.15, COORD_DECIMALS)
    widths = [(1.2, 0.5, "sky-column-1"), (0.8, 0.34, "sky-column-2"), (0.45, 0.2, "sky-column-3")]
    for w_bot, w_top, kind in widths:
        quad = [[SKY_BASE[0] - w_bot / 2, SKY_BASE[1]], [SKY_BASE[0] + w_bot / 2, SKY_BASE[1]],
                [SKY_BASE[0] + w_top / 2, top_lat], [SKY_BASE[0] - w_top / 2, top_lat]]
        quad.append(quad[0])
        out.append(feat(slug, debut, kind, 0, poly(quad)))
    # two jet lines inside the stream
    for off in (-0.11, 0.11):
        out.append(feat(slug, debut, "sky-jet", 0, line(
            [[SKY_BASE[0] + off * 2.2, SKY_BASE[1] + 0.15],
             [SKY_BASE[0] + off, top_lat - 0.3]])))
    return out


BUILDERS = {
    "punk-hazard": punk_hazard,
    "arabasta-kingdom": arabasta,
    "skypiea": skypiea,
}


def main() -> int:
    islands = {i["slug"]: i for i in json.loads((GENERATED / "islands.json").read_text())}
    coords = {c["slug"]: c for c in json.loads((CANON_DIR / "islands.coords.json").read_text())["islands"]}
    voyage = json.loads((CANON_DIR / "voyage_legs.json").read_text())
    presence = json.loads((CANON_DIR / "crew_presence.json").read_text())
    biome_overrides = json.loads((CANON_DIR / "islands.biomes.json").read_text())["biomes"]

    voyage_slugs = {w["slug"] for w in voyage["waypoints"] if w.get("slug")}
    anchor_slugs = set()
    for c in presence.get("crews", []) + presence.get("characters", []):
        for w in c.get("windows", []):
            if w.get("island_slug"):
                anchor_slugs.add(w["island_slug"])

    features: list[dict] = []
    for slug, builder in BUILDERS.items():
        assert slug in HERO_SLUGS, f"{slug} must be in gen_silhouettes.HERO_SLUGS (128-pt ring)"
        isl, pos = islands[slug], coords[slug]
        debut = isl["debut_chapter"]
        assert isinstance(debut, int), f"{slug} has no debut chapter"
        biome = biome_for(isl, pos.get("sea"), biome_overrides)
        ring = HeroRing(isl, pos, biome, voyage_slugs, anchor_slugs)
        features.extend(builder(ring, slug, debut))

    fc = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/gen_terrain.py",
            "license": "Original generated geometry — MIT, same as the code.",
            "note": "Deterministic per-slug: regenerating without input changes is a no-op diff. "
                    "Shapes are polar fractions of each island's silhouette ring (same seed), "
                    "so terrain always sits inside its coastline.",
            "heroes": sorted(BUILDERS),
            "features": len(features),
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(fc, separators=(",", ":")) + "\n")
    kb = OUT_PATH.stat().st_size // 1024
    print(f"islands.terrain.json: {len(features)} terrain features "
          f"across {len(BUILDERS)} hero islands, {kb} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
