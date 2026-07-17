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
from gen_silhouettes import (
    COORD_DECIMALS, HERO_SLUGS, Rng, load_islands, profile_for, radius_fn,
    inputs_sha as sil_inputs_sha,
)

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


# MUST MATCH components/fishman.ts:DIVE_BASE. The scar on the surface and the
# ship that dives through it are drawn by two different systems; if these drift,
# the ship goes under in one place and the water closes over in another.
DIVE_BASE = (-48.2843, 2.9)


def fish_man_island(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    """The mirror of skypiea(). Ten thousand metres DOWN instead of up, so the
    same three ideas invert: the island is domed instead of open to the air, the
    sea above it is a weight instead of a lift, and the mark on the surface is a
    scar the ship left rather than a stream carrying it."""
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []

    # THE ABYSS VEIL: an annulus OUTSIDE the coast. Skypiea's shadow says
    # "there is nothing under me"; this says "there are ten thousand metres of
    # water on top of me". Sort 0 so it lies beneath everything else.
    veil = ring.ring(1.18, wobble=0.05, wobble_freq=4, wobble_phase=rng.range(0, TAU))
    out.append(feat(slug, debut, "abyss-veil", 0, poly(veil)))

    # THE SEABED. The island's own footprint, filled dark, because everything
    # above this is the biome system telling the truth about the wrong axis:
    # Fish-Man Island classifies as temperate, which is correct (it is warm and
    # green down there) and paints it the same meadow-olive as Syrup Village.
    # Ten thousand metres of water is not a climate, so the depth is painted
    # here as terrain rather than fought over in biomes.py.
    out.append(feat(slug, debut, "seabed", 1,
                    poly(ring.ring(0.995, wobble=0.01, wobble_freq=3,
                                   wobble_phase=rng.range(0, TAU)))))

    # THE BUBBLE: concentric rings of the dome that keeps the sea out. Drawn as
    # lines, not fills — you are meant to see the island THROUGH it.
    for t, kind in ((0.99, "bubble-dome-outer"), (0.82, "bubble-dome-inner")):
        out.append(feat(slug, debut, kind, 5, line(
            ring.ring(t, wobble=0.03, wobble_freq=6, wobble_phase=rng.range(0, TAU)))))
    # the highlight arc — where the light catches the dome
    out.append(feat(slug, debut, "dome-highlight", 6, line(ring.arc(0.5, 2.0, 0.93))))

    # CORAL. Clustered toward the middle, in two inks so the seabed reads as
    # grown rather than printed.
    for i in range(7):
        th = rng.range(0, TAU)
        t = rng.range(0.28, 0.72)
        kind = "coral-a" if i % 2 == 0 else "coral-b"
        out.append(feat(slug, debut, kind, 2 + (i % 2),
                        poly(ring.small_blob(rng, th, t, rng.range(0.1, 0.22)))))

    # THE SCAR: where the coated ship went under, off Sabaody. Two stacked
    # ellipses — the inverse of the sky shadow, which is two stacked rings of
    # the island. This one is not the island's shape: nothing up there is
    # casting it. It is just water closing over.
    for rx, ry, kind in ((0.62, 0.34, "shimmer-soft"), (0.34, 0.19, "shimmer-core")):
        pts = []
        for i in range(49):
            th = TAU * i / 48
            pts.append([round(DIVE_BASE[0] + math.cos(th) * rx, COORD_DECIMALS),
                        round(DIVE_BASE[1] + math.sin(th) * ry, COORD_DECIMALS)])
        out.append(feat(slug, debut, kind, 0, poly(pts)))
    return out


# ---------------------------------------------------------------------------
# Thriller Bark — not an island. A ship, the largest ever built, with a whole
# arc's worth of story standing on its deck. So it is drawn as what it is: a
# hull with a rail, three masts, rigging, and the graveyard fog it drags along.
# ---------------------------------------------------------------------------

def thriller_bark(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    # The keel IS the long axis: profile_for gives a Ship a hull-shaped f(theta)
    # pinched at theta 0 and pi, so bow and stern are there and nowhere else.
    # (rng.range is still called: the seed stream must not shift.)
    rng.range(0, TAU)
    keel = 0.0

    out.append(feat(slug, debut, "hull-deck", 1, poly(ring.ring(0.97))))
    out.append(feat(slug, debut, "hull-rail", 5, line(ring.ring(0.9))))

    # three masts along the keel, tallest amidships, each with a spar
    for i, (t, size) in enumerate(((0.62, 0.15), (0.0, 0.2), (-0.62, 0.16))):
        th = keel if t >= 0 else keel + math.pi
        at = abs(t)
        out.append(feat(slug, debut, "mast", 3,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:mast{i}"), th, at, size))))
        # the spar: a chord across the keel at this mast
        p0 = ring.pt(th + 0.42, at + 0.16)
        p1 = ring.pt(th - 0.42, at + 0.16)
        out.append(feat(slug, debut, "rigging", 4, line([p0, p1])))

    # rigging: lines from the bow and the stern up to the mainmast
    bow, stern = ring.pt(keel, 0.9), ring.pt(keel + math.pi, 0.9)
    main = ring.pt(keel, 0.0)
    for end in (bow, stern):
        out.append(feat(slug, debut, "rigging", 4, line([end, main])))

    # the fog it drags with it. Sort 6: OVER everything, because that is what
    # fog does — the Florian Triangle is the point of the place.
    for i in range(3):
        th = rng.range(0, TAU)
        t = rng.range(0.3, 0.8)
        out.append(feat(slug, debut, "grave-fog", 6,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:fog{i}"), th, t,
                                             rng.range(0.16, 0.26)))))
    return out


# ---------------------------------------------------------------------------
# Whole Cake Island — a cake. Tiers, icing running down the sides, and the
# candy that grows on it.
# ---------------------------------------------------------------------------

def whole_cake(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []

    # the tiers, alternating sponge and cream, each smaller than the last
    for i, t in enumerate((0.88, 0.66, 0.44, 0.24)):
        kind = "cake-tier-a" if i % 2 == 0 else "cake-tier-b"
        out.append(feat(slug, debut, kind, 1 + i,
                        poly(ring.ring(t, wobble=0.05, wobble_freq=7,
                                       wobble_phase=rng.range(0, TAU)))))

    # icing: it runs DOWN from the top tier, so each drip starts at the middle
    # and falls outward. Two of them, on opposite-ish sides.
    for i in range(2):
        th0 = rng.range(0, TAU)
        pts = []
        steps = 18
        for s in range(steps + 1):
            t = 0.2 + (0.95 - 0.2) * s / steps
            wobble = 0.16 * math.sin(3.5 * s / steps + i)
            pts.append(ring.pt(th0 + wobble, t))
        out.append(feat(slug, debut, "icing-river", 6, line(pts)))

    # candy — scattered on the tiers
    for i in range(9):
        th = rng.range(0, TAU)
        t = rng.range(0.3, 0.8)
        out.append(feat(slug, debut, "candy-dot", 7,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:candy{i}"), th, t,
                                             rng.range(0.04, 0.08)))))
    return out


# ---------------------------------------------------------------------------
# Water 7 — the city of water: ring canals, a fountain at the centre, and the
# shipyard docks on the seaward side.
# ---------------------------------------------------------------------------

def water_7(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    out.append(feat(slug, debut, "city-ground", 1, poly(ring.ring(0.96))))
    for t in (0.82, 0.62, 0.42):
        out.append(feat(slug, debut, "canal", 5,
                        line(ring.ring(t, wobble=0.02, wobble_freq=5,
                                       wobble_phase=rng.range(0, TAU)))))
    # the fountain: a spiral from the centre out, tight
    pts = []
    th0 = rng.range(0, TAU)
    for s in range(41):
        th = th0 + 3.4 * s / 40
        pts.append(ring.pt(th, 0.04 + 0.3 * s / 40))
    out.append(feat(slug, debut, "fountain", 6, line(pts)))
    # docks on the coast, clustered on one side (the yard faces the sea lane)
    face = rng.range(0, TAU)
    for i in range(4):
        out.append(feat(slug, debut, "dock", 3,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:dock{i}"),
                                             face + (i - 1.5) * 0.34, 0.86,
                                             rng.range(0.07, 0.11)))))
    return out


# ---------------------------------------------------------------------------
# Enies Lobby — an island standing over a hole. The sea pours off every edge,
# which is why the whole arc is about getting OFF it.
# ---------------------------------------------------------------------------

def enies_lobby(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    # the chasm: an annulus OUTSIDE the coast, near-black. Sort 0 — under
    # everything, including the island it is swallowing.
    out.append(feat(slug, debut, "chasm", 0,
                    poly(ring.ring(1.32, wobble=0.06, wobble_freq=5,
                                   wobble_phase=rng.range(0, TAU)))))
    out.append(feat(slug, debut, "court-ground", 1, poly(ring.ring(0.95))))
    # the falls: radial lines pouring over the rim
    for i in range(10):
        th = TAU * i / 10 + rng.range(-0.1, 0.1)
        out.append(feat(slug, debut, "falls", 4, line([ring.pt(th, 0.92), ring.pt(th, 1.28)])))
    # the tower at the centre
    out.append(feat(slug, debut, "tower", 5,
                    poly(ring.small_blob(rng, 0, 0.0, 0.16))))
    return out


# ---------------------------------------------------------------------------
# Marineford — a crescent bay with the fortress closing it. The whole war is
# fought in the bowl between them.
# ---------------------------------------------------------------------------

def marineford(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    face = rng.range(0, TAU)  # the bay faces this way
    out.append(feat(slug, debut, "fort-ground", 1, poly(ring.ring(0.96))))
    # the bay: a wedge of sea cut into the island, mouth on the coast
    bay = ring.arc(face - 1.05, face + 1.05, 0.92)
    bay.append(ring.pt(face, 0.12))
    bay.append(bay[0])
    out.append(feat(slug, debut, "bay-water", 3, poly(bay)))
    # the fortress: a band opposite the bay
    band = ring.arc(face + math.pi - 1.0, face + math.pi + 1.0, 0.82)
    band += list(reversed(ring.arc(face + math.pi - 1.0, face + math.pi + 1.0, 0.52)))
    band.append(band[0])
    out.append(feat(slug, debut, "fortress", 4, poly(band)))
    # the execution platform, in the middle of the bowl
    out.append(feat(slug, debut, "tower", 5, poly(ring.small_blob(rng, face + math.pi, 0.3, 0.09))))
    return out


# ---------------------------------------------------------------------------
# Impel Down — six levels, each one further down. Drawn as rings darkening
# inward, because down is the only direction that place has.
# ---------------------------------------------------------------------------

def impel_down(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    for i, t in enumerate((0.94, 0.78, 0.62, 0.46, 0.30)):
        out.append(feat(slug, debut, f"prison-level-{i % 2}", 1 + i,
                        poly(ring.ring(t, wobble=0.015, wobble_freq=8,
                                       wobble_phase=rng.range(0, TAU)))))
        out.append(feat(slug, debut, "prison-ring", 6, line(ring.ring(t))))
    out.append(feat(slug, debut, "tower", 7, poly(ring.small_blob(rng, 0, 0.0, 0.1))))
    return out


# ---------------------------------------------------------------------------
# Drum Island — the drums: flat-topped cylinder peaks in the snow.
# ---------------------------------------------------------------------------

def drum_island(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    out.append(feat(slug, debut, "snowfield", 1, poly(ring.ring(0.96))))
    for i in range(4):
        th = rng.range(0, TAU)
        t = rng.range(0.2, 0.6)
        size = rng.range(0.12, 0.19)
        out.append(feat(slug, debut, "drum-peak", 2,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:peak{i}"), th, t, size))))
        # the flat top — a smaller blob inside, paler: that IS the drum read
        out.append(feat(slug, debut, "drum-cap", 3,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:cap{i}"), th, t, size * 0.55))))
    return out


# ---------------------------------------------------------------------------
# Zou — an island on the back of an elephant. The island is what you see; the
# trunk is what tells you what you are standing on.
# ---------------------------------------------------------------------------

def zou(ring: HeroRing, slug: str, debut: int) -> list[dict]:
    rng = Rng(f"terrain:{slug}")
    out: list[dict] = []
    out.append(feat(slug, debut, "back-ground", 1, poly(ring.ring(0.95))))
    # the whale tree, off-centre, where the Road Poneglyph lives
    out.append(feat(slug, debut, "whale-tree", 4, poly(ring.small_blob(rng, 1.2, 0.35, 0.14))))
    # the trunk: leaves the coast and curls out over the sea. The one mark that
    # says this is not an island.
    th0 = rng.range(0, TAU)
    pts = []
    for s in range(19):
        f = s / 18
        pts.append(ring.pt(th0 + 0.55 * f * f, 0.9 + 0.5 * f))
    out.append(feat(slug, debut, "trunk", 5, line(pts)))
    # and the legs it stands on — four stumps under the rim
    for i in range(4):
        th = th0 + math.pi + (i - 1.5) * 0.5
        out.append(feat(slug, debut, "leg", 0,
                        poly(ring.small_blob(Rng(f"terrain:{slug}:leg{i}"), th, 1.05, 0.1))))
    return out


BUILDERS = {
    "punk-hazard": punk_hazard,
    "arabasta-kingdom": arabasta,
    "skypiea": skypiea,
    "fish-man-island": fish_man_island,
    "thriller-bark": thriller_bark,
    "whole-cake-island": whole_cake,
    "water-7": water_7,
    "enies-lobby": enies_lobby,
    "marineford": marineford,
    "impel-down": impel_down,
    "drum-island": drum_island,
    "zou": zou,
}

# Terrain reveals when the island is SEEN, which is not always when it is NAMED.
#
# For every hero but one those are the same chapter, so `debut` is the gate. Not
# for Fish-Man Island: its debut_chapter is 68, because Arlong says the name in
# East Blue — five hundred chapters before anyone goes there. That is a correct
# fog key for the PIN (the reader does learn the place exists at 68) and a
# terrible one for the terrain, which would let a chapter-100 reader zoom in and
# find the bubble dome, the coral, and the shape of a city nobody has visited.
#
# A name is not a photograph. This is where that distinction gets written down.
TERRAIN_SEEN = {
    "fish-man-island": 604,  # the crew comes through the bottom of the descent
}


def main() -> int:
    islands = {i["slug"]: i for i in load_islands()}
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
        debut = TERRAIN_SEEN.get(slug, isl["debut_chapter"])
        assert isinstance(debut, int), f"{slug} has no debut chapter"
        assert debut >= isl["debut_chapter"], (
            f"{slug}: terrain would reveal at ch. {debut}, BEFORE the island itself is charted "
            f"at ch. {isl['debut_chapter']} — painted ground on a fogged pin"
        )
        biome = biome_for(isl, pos.get("sea"), biome_overrides)
        ring = HeroRing(isl, pos, biome, voyage_slugs, anchor_slugs)
        features.extend(builder(ring, slug, debut))

    fc = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/gen_terrain.py",
            # Same fingerprint as the silhouettes, and for the same reason: this
            # geometry is derived from each island's ring, which is itself
            # derived from presence and the voyage. See gen_silhouettes.
            "inputs_sha": sil_inputs_sha(),
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
