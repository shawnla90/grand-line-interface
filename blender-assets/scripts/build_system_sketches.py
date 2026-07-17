#!/usr/bin/env python3
"""Generate original SVG system sketches from verified visual contracts."""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
OUT = ROOT / "sketches"


def read(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:12], 16)


def island_points(cx: float, cy: float, rx: float, ry: float, slug: str) -> str:
    rng = random.Random(stable_int(slug))
    points = []
    for index in range(14):
        angle = math.tau * index / 14
        wobble = rng.uniform(0.78, 1.16)
        x = cx + math.cos(angle) * rx * wobble
        y = cy + math.sin(angle) * ry * wobble
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def svg_shell(title: str, body: str, width: int = 1800, height: int = 1200) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<title>{escape(title)}</title>
<defs>
  <radialGradient id="ocean" cx="50%" cy="45%"><stop offset="0" stop-color="#153e54"/><stop offset="1" stop-color="#06131d"/></radialGradient>
  <linearGradient id="cake" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff2bd"/><stop offset=".5" stop-color="#ef9fb9"/><stop offset="1" stop-color="#8f456b"/></linearGradient>
  <linearGradient id="steel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dce8ed"/><stop offset=".5" stop-color="#647a86"/><stop offset="1" stop-color="#1d2b34"/></linearGradient>
  <filter id="glow"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#78d6e7"/></marker>
</defs>
{body}
</svg>\n'''


def build_totto(contract: dict[str, Any]) -> str:
    width, height = 1800, 1200
    cx, cy = 900, 560
    ring_radii = (255, 385, 515)
    ring_counts = (10, 12, 16)
    direction_angles = {
        "north": -90,
        "northeast": -45,
        "east": 0,
        "southeast": 45,
        "south": 90,
        "southwest": 135,
        "west": 180,
        "northwest": 225,
    }
    slots: list[dict[str, Any]] = []
    for ring_index, (radius, count) in enumerate(zip(ring_radii, ring_counts)):
        offset = -90 + (ring_index * 7.5)
        for index in range(count):
            angle = offset + 360 * index / count
            slots.append({"ring": ring_index, "angle": angle, "radius": radius, "used": False})

    def angular_distance(a: float, b: float) -> float:
        return abs((a - b + 180) % 360 - 180)

    def take_slot(direction: str | None, ring: str | None) -> dict[str, Any]:
        candidates = [slot for slot in slots if not slot["used"]]
        if ring == "innermost":
            candidates = [slot for slot in candidates if slot["ring"] == 0]
        elif ring == "outermost":
            candidates = [slot for slot in candidates if slot["ring"] == 2]
        if direction:
            target = direction_angles[direction]
            candidates.sort(key=lambda slot: (angular_distance(slot["angle"], target), slot["ring"]))
        else:
            candidates.sort(key=lambda slot: (slot["ring"], stable_int(str(slot["angle"]))))
        slot = candidates[0]
        slot["used"] = True
        return slot

    components = contract["identity"]["subsidiaries"]
    known = [item for item in components if item["relative_placement"]["direction"]]
    unknown = [item for item in components if not item["relative_placement"]["direction"]]
    placed: list[tuple[dict[str, Any], dict[str, Any], bool]] = []
    for item in sorted(known, key=lambda value: (value["relative_placement"]["direction"], value["slug"])):
        hint = item["relative_placement"]
        placed.append((item, take_slot(hint["direction"], hint["ring"]), True))
    for item in sorted(unknown, key=lambda value: value["slug"]):
        placed.append((item, take_slot(None, None), False))

    parts = [
        '<rect width="1800" height="1200" fill="url(#ocean)"/>',
        '<text x="70" y="82" fill="#fff6de" font-family="Georgia,serif" font-size="48">TOTTO LAND — SYSTEM SKETCH 01</text>',
        '<text x="72" y="122" fill="#8fb9c4" font-family="Arial,sans-serif" font-size="20">1 central island + 34 subsidiary islands • solid = cited bearing • dashed = unresolved placement</text>',
        '<text x="1718" y="82" text-anchor="end" fill="#f0c66b" font-family="Arial,sans-serif" font-size="18">NOT CANON SCALE</text>',
    ]
    for radius in ring_radii:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#d7b25a" stroke-width="2" stroke-dasharray="7 15" opacity=".38"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="560" fill="none" stroke="#f8dff1" stroke-width="17" stroke-dasharray="1 22" stroke-linecap="round" opacity=".32"/>')

    for item, slot, placement_known in placed:
        angle = math.radians(slot["angle"])
        x = cx + math.cos(angle) * slot["radius"]
        y = cy + math.sin(angle) * slot["radius"] * 0.76
        hue = stable_int(item["theme_hint"]["theme"]) % 360
        color = f"hsl({hue} 65% 62%)"
        dash = "" if placement_known else ' stroke-dasharray="7 6"'
        stroke = "#fff4dc" if placement_known else "#79939d"
        points = island_points(x, y, 39 if slot["ring"] < 2 else 34, 25, item["slug"])
        short_name = item["name"].replace(" Island", "")
        number = components.index(item) + 1
        parts.extend([
            f'<ellipse cx="{x:.1f}" cy="{y + 12:.1f}" rx="46" ry="23" fill="#000" opacity=".26"/>',
            f'<polygon points="{points}" fill="{color}" stroke="{stroke}" stroke-width="3"{dash}/>',
            f'<circle cx="{x - 8:.1f}" cy="{y - 8:.1f}" r="8" fill="#fff7db" opacity=".48"/>',
            f'<text x="{x:.1f}" y="{y + 46:.1f}" text-anchor="middle" fill="#e9f1ee" font-family="Arial,sans-serif" font-size="12">{number:02d} {escape(short_name)}</text>',
        ])

    # Central Whole Cake Island is intentionally a unique landmark mass.
    parts.extend([
        f'<ellipse cx="{cx}" cy="{cy + 62}" rx="130" ry="48" fill="#000" opacity=".34"/>',
        f'<ellipse cx="{cx}" cy="{cy + 35}" rx="118" ry="58" fill="#82435f" stroke="#ffe1b1" stroke-width="4"/>',
        f'<rect x="{cx - 96}" y="{cy - 20}" width="192" height="58" rx="22" fill="url(#cake)" stroke="#ffe1b1" stroke-width="4"/>',
        f'<ellipse cx="{cx}" cy="{cy - 19}" rx="96" ry="38" fill="#fff0bc" stroke="#ffe1b1" stroke-width="4"/>',
        f'<rect x="{cx - 58}" y="{cy - 76}" width="116" height="58" rx="18" fill="#ef9fb9" stroke="#ffe1b1" stroke-width="4"/>',
        f'<ellipse cx="{cx}" cy="{cy - 76}" rx="58" ry="25" fill="#fff6cf" stroke="#ffe1b1" stroke-width="4"/>',
        f'<path d="M{cx - 28} {cy - 92} L{cx - 13} {cy - 155} L{cx} {cy - 110} L{cx + 16} {cy - 168} L{cx + 31} {cy - 92}Z" fill="#f3d06b" stroke="#fff1bd" stroke-width="4" filter="url(#glow)"/>',
        f'<text x="{cx}" y="{cy + 103}" text-anchor="middle" fill="#fff7dc" font-family="Georgia,serif" font-size="20">WHOLE CAKE ISLAND — CENTRAL</text>',
    ])

    parts.extend([
        '<rect x="64" y="1010" width="1672" height="126" rx="18" fill="#07151d" stroke="#2d5968"/>',
        '<text x="92" y="1052" fill="#f0c66b" font-family="Arial,sans-serif" font-size="17">BLENDER BUILD RULE</text>',
        '<text x="92" y="1085" fill="#d5e4e7" font-family="Arial,sans-serif" font-size="18">Each numbered island becomes its own collection, silhouette, material research lane, and LOD set.</text>',
        '<text x="92" y="1116" fill="#8fb9c4" font-family="Arial,sans-serif" font-size="16">The rings are a topology scaffold. Unknown bearings remain unresolved instead of being disguised as canon.</text>',
    ])
    return svg_shell("Totto Land system sketch", "\n".join(parts), width, height)


def build_tarai(contract: dict[str, Any]) -> str:
    names = {item["slug"]: item["name"] for item in contract["identity"]["components"]}
    parts = [
        '<rect width="1800" height="1200" fill="url(#ocean)"/>',
        '<text x="70" y="82" fill="#eef3f2" font-family="Georgia,serif" font-size="48">WORLD GOVERNMENT — TARAI SYSTEM SKETCH 01</text>',
        '<text x="72" y="122" fill="#8fb9c4" font-family="Arial,sans-serif" font-size="20">Relational pre-timeskip topology • chapter state changes at 598 • atlas jitter excluded</text>',
        '<rect x="1450" y="52" width="282" height="55" rx="28" fill="#6f2634" stroke="#f2a6ac" stroke-width="2"/>',
        '<text x="1591" y="87" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="18">PRE-TIMESKIP ACTIVE</text>',
        '<path d="M390 390 Q900 115 1410 390 Q1530 720 900 930 Q270 720 390 390Z" fill="none" stroke="#76d8e7" stroke-width="24" opacity=".18"/>',
        '<path d="M425 410 Q900 170 1375 410 Q1450 690 900 870 Q350 690 425 410Z" fill="none" stroke="#78d6e7" stroke-width="7" stroke-dasharray="24 16" marker-end="url(#arrow)"/>',
        '<path d="M790 430 C1110 260 1240 700 910 760 C575 820 560 455 830 360 C1060 282 1135 565 910 650 C690 732 645 500 820 438" fill="none" stroke="#b5f3f0" stroke-width="11" opacity=".64" marker-end="url(#arrow)"/>',
        '<text x="900" y="560" text-anchor="middle" fill="#d7ffff" font-family="Georgia,serif" font-size="30">TARAI CURRENT</text>',
        '<text x="900" y="592" text-anchor="middle" fill="#78aeb9" font-family="Arial,sans-serif" font-size="16">controlled current / private fast-travel system</text>',
    ]

    # Enies Lobby: judicial mass over an impossible vertical void/waterfall.
    parts.extend([
        '<g transform="translate(365 340)">',
        '<ellipse cx="0" cy="86" rx="144" ry="54" fill="#0b1116" opacity=".5"/>',
        '<path d="M-124 45 Q0 -20 124 45 L92 105 Q0 145 -92 105Z" fill="#b9c9c6" stroke="#edf1e9" stroke-width="5"/>',
        '<path d="M-84 102 Q0 180 84 102 L54 260 Q0 330 -54 260Z" fill="#79d7e6" opacity=".45"/>',
        '<rect x="-52" y="-22" width="104" height="82" fill="url(#steel)" stroke="#f0f1e6" stroke-width="4"/>',
        '<path d="M-70 -22 L0 -92 L70 -22Z" fill="#dce3dc" stroke="#f0f1e6" stroke-width="4"/>',
        '</g>',
        f'<text x="365" y="700" text-anchor="middle" fill="#fff" font-family="Georgia,serif" font-size="29">{escape(names["enies-lobby"])}</text>',
        '<text x="365" y="730" text-anchor="middle" fill="#9bb6bd" font-family="Arial,sans-serif" font-size="16">judicial facility / waterfall void</text>',
    ])

    # Marineford: surface fortress and crescent harbor.
    parts.extend([
        '<g transform="translate(1435 355)">',
        '<path d="M-150 110 Q0 35 150 110 Q95 205 0 185 Q-95 205 -150 110Z" fill="#596d75" stroke="#d6e1df" stroke-width="5"/>',
        '<path d="M-100 100 Q0 168 100 100" fill="none" stroke="#8be3ec" stroke-width="15"/>',
        '<rect x="-76" y="5" width="152" height="104" fill="url(#steel)" stroke="#e6edeb" stroke-width="4"/>',
        '<rect x="-42" y="-65" width="84" height="72" fill="#798b91" stroke="#e6edeb" stroke-width="4"/>',
        '<circle cx="0" cy="-29" r="20" fill="#e6edeb"/><path d="M-12 -29H12M0 -41V-17" stroke="#30444e" stroke-width="5"/>',
        '</g>',
        f'<text x="1435" y="700" text-anchor="middle" fill="#fff" font-family="Georgia,serif" font-size="29">{escape(names["marineford"])}</text>',
        '<text x="1435" y="730" text-anchor="middle" fill="#9bb6bd" font-family="Arial,sans-serif" font-size="16">Marine HQ in this historical variant</text>',
    ])

    # Impel Down: tiny surface cap with the actual prison mass below water.
    parts.extend([
        '<g transform="translate(900 870)">',
        '<line x1="-235" y1="0" x2="235" y2="0" stroke="#75d7e5" stroke-width="7"/>',
        '<ellipse cx="0" cy="0" rx="92" ry="25" fill="#151f25" stroke="#c9d4d5" stroke-width="4"/>',
        '<path d="M-70 0 L-52 205 Q0 278 52 205 L70 0Z" fill="#182128" stroke="#8ea1a8" stroke-width="5"/>',
        '<path d="M-55 44H55M-52 85H52M-48 126H48M-43 167H43M-32 208H32" stroke="#d04e45" stroke-width="6" opacity=".8"/>',
        '<circle cx="0" cy="235" r="34" fill="#f0643b" opacity=".8" filter="url(#glow)"/>',
        '</g>',
        f'<text x="900" y="1140" text-anchor="middle" fill="#fff" font-family="Georgia,serif" font-size="29">{escape(names["impel-down"])}</text>',
        '<text x="900" y="1170" text-anchor="middle" fill="#9bb6bd" font-family="Arial,sans-serif" font-size="16">underwater prison / depth is the primary form</text>',
    ])

    # Three distributed gates; the API has one entity, the visual system has instances.
    for x, y, rotation in ((565, 360, -18), (1235, 360, 18), (900, 782, 0)):
        parts.append(f'''<g transform="translate({x} {y}) rotate({rotation})">
<rect x="-46" y="-70" width="30" height="140" fill="url(#steel)" stroke="#eef1ea" stroke-width="3"/>
<rect x="16" y="-70" width="30" height="140" fill="url(#steel)" stroke="#eef1ea" stroke-width="3"/>
<path d="M-16 -52 Q0 -70 16 -52V52Q0 70 -16 52Z" fill="#692b35" stroke="#f1b3ad" stroke-width="3"/>
</g>''')
    parts.extend([
        '<text x="900" y="188" text-anchor="middle" fill="#f1c6ba" font-family="Arial,sans-serif" font-size="20">GATES OF JUSTICE = DISTRIBUTED ACCESS INFRASTRUCTURE</text>',
        '<rect x="74" y="905" width="540" height="178" rx="18" fill="#07151d" stroke="#2d5968"/>',
        '<text x="101" y="946" fill="#f0c66b" font-family="Arial,sans-serif" font-size="17">BLENDER COLLECTIONS</text>',
        '<text x="101" y="980" fill="#d5e4e7" font-family="Arial,sans-serif" font-size="17">Facilities • gate instances • current volume</text>',
        '<text x="101" y="1012" fill="#d5e4e7" font-family="Arial,sans-serif" font-size="17">water surface • underwater depth • era states</text>',
        '<text x="101" y="1054" fill="#8fb9c4" font-family="Arial,sans-serif" font-size="15">Do not build five unrelated island plates.</text>',
        '<rect x="1185" y="905" width="540" height="178" rx="18" fill="#07151d" stroke="#6f4650" stroke-dasharray="9 7"/>',
        '<text x="1212" y="946" fill="#ef9ca6" font-family="Arial,sans-serif" font-size="17">CHAPTER 598 STATE CHANGE</text>',
        '<text x="1212" y="980" fill="#d5e4e7" font-family="Arial,sans-serif" font-size="17">Old Marineford becomes a former node.</text>',
        '<text x="1212" y="1012" fill="#d5e4e7" font-family="Arial,sans-serif" font-size="17">New Marineford is not substituted into this triangle.</text>',
        '<text x="1212" y="1054" fill="#8fb9c4" font-family="Arial,sans-serif" font-size="15">Post-timeskip topology remains a research question.</text>',
    ])
    return svg_shell("World Government Tarai system sketch", "\n".join(parts))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {
        "totto-land-system.svg": (
            "totto-land.visual.json",
            build_totto,
        ),
        "world-government-tarai-system.svg": (
            "world-government-tarai-system.visual.json",
            build_tarai,
        ),
    }
    outputs = []
    for filename, (contract_name, builder) in jobs.items():
        contract = read(contract_name)
        path = OUT / filename
        path.write_text(builder(contract), encoding="utf-8")
        preview = OUT / "previews" / filename.replace(".svg", ".png")
        preview.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(preview)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        outputs.append(
            {
                "id": contract["id"],
                "contract": f"contracts/{contract_name}",
                "contract_sha256": sha(CONTRACTS / contract_name),
                "sketch": f"sketches/{filename}",
                "sketch_sha256": sha(path),
                "preview": str(preview.relative_to(ROOT)),
                "preview_sha256": sha(preview),
                "status": "system_sketch_not_final_art",
            }
        )
        print(f"wrote {path}")
    manifest = {
        "schema_version": 1,
        "generator": "scripts/build_system_sketches.py",
        "coordinate_policy": "relational schematic; no atlas coordinate geometry",
        "outputs": outputs,
    }
    manifest_path = OUT / "sketch-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
