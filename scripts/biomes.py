#!/usr/bin/env python3
"""
biomes.py — deterministic biome classification, shared by the geometry
generators (gen_silhouettes.py, gen_terrain.py). MACHINE-OWNED logic; the
human door is canon/islands.biomes.json (override wins over every heuristic).

A biome is a PAINT KEY, not a fact claim: it decides which chart ink an
island's landmass uses (and, for hero islands, which terrain set). The wiki
only fills `island_type` for 15/413 islands, so most of the map rides the
temperate default until a human or the wiki says otherwise.

No latitude heuristic on purpose: this chart's latitudes encode the belt
model (voyage progress), not climate.
"""

from __future__ import annotations

BIOMES = {"temperate", "winter", "summer", "desert", "jungle", "volcanic", "sky"}

# wiki Island Box `type` substrings -> biome (checked in order)
_TYPE_MAP = [
    ("winter", "winter"),
    ("summer", "summer"),
    ("prehistoric", "jungle"),
    ("desert", "desert"),
    ("sky", "sky"),
]

# island-name substrings -> biome (checked in order; conservative on purpose —
# a wrong tint is a canon bug someone has to notice, silence is just default ink)
_NAME_KEYWORDS = [
    (("desert", "sand", "dune"), "desert"),
    (("snow", "ice", "winter"), "winter"),
    (("volcan", "hazard"), "volcanic"),
    (("sky", "cloud", "heaven"), "sky"),
    (("jungle",), "jungle"),
]


def biome_for(island: dict, sea: str | None, overrides: dict[str, str]) -> str:
    """Resolve an island's biome. `sea` must come from canon/islands.coords.json
    (data/generated/islands.json has sea=null for wiki pages that omit it —
    Skypiea's own sea is only recorded in the coords file)."""
    ov = overrides.get(island["slug"])
    if ov:
        return ov
    t = (island.get("island_type") or "").lower()
    for needle, biome in _TYPE_MAP:
        if needle in t:
            return biome
    if (sea or island.get("sea")) == "Sky":
        return "sky"
    name = island["name"].lower()
    for needles, biome in _NAME_KEYWORDS:
        if any(n in name for n in needles):
            return biome
    return "temperate"
