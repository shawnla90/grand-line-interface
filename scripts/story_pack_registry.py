"""Derive the generated story-pack registry from the synced artifacts.

The app selects and imports saga packs through config/story-packs.generated.ts.
That file is EMITTED, never hand-edited: literal import() paths are how Next
emits one optional chunk per signed pack, so the registry must be a real
source file — but its contents are pure data derivable from the artifacts in
data/generated/. This module is the single place that derivation lives;
sync_story_simulation_pack.py emits through it and check_story_simulations.py
re-derives through it to prove the file on disk has not drifted.

Byte-stable output (no timestamps) — the compile_scene_playback.py posture.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_TS = ROOT / "config/story-packs.generated.ts"

# East Blue predates the generic pipeline and keeps its legacy artifact path.
# Every later pack lives under data/generated/story_simulations/<id>.json.
LEGACY_ARTIFACTS = {
    "east-blue-saga-2d": ROOT / "data/generated/east_blue_simulations.json",
}
PACK_DIR = ROOT / "data/generated/story_simulations"


class RegistryError(Exception):
    pass


def discover_artifacts() -> dict[str, Path]:
    """All synced pack artifacts on disk, keyed by pack id."""
    artifacts = {pid: path for pid, path in LEGACY_ARTIFACTS.items() if path.is_file()}
    for path in sorted(PACK_DIR.glob("*.json")):
        meta = json.loads(path.read_text()).get("_meta") or {}
        pack_id = meta.get("pack_id")
        if pack_id != path.stem:
            raise RegistryError(
                f"{path.name}: _meta.pack_id {pack_id!r} disagrees with the filename"
            )
        artifacts[pack_id] = path
    return artifacts


def _aliases(pack_id: str) -> list[str]:
    """Short alias = the saga name before '-saga-'. Deterministic, no table."""
    head = pack_id.split("-saga-")[0]
    return [head] if head and head != pack_id else []


def derive_rows() -> list[dict]:
    rows = []
    for pack_id, path in discover_artifacts().items():
        doc = json.loads(path.read_text())
        gates = [s["chapter_gate"]["start"] for s in doc["scenes"]]
        if not gates:
            raise RegistryError(f"{pack_id}: artifact has zero runtime-ready scenes")
        rows.append(
            {
                "id": pack_id,
                "aliases": _aliases(pack_id),
                "first_scene_chapter": min(gates),
                "import_path": "@/" + path.relative_to(ROOT).as_posix(),
            }
        )
    # Newest saga first: the pack whose scenes open latest owns the globe.
    rows.sort(key=lambda r: (-r["first_scene_chapter"], r["id"]))
    return rows


def render_ts(rows: list[dict]) -> str:
    entries = []
    for row in rows:
        aliases = ", ".join(json.dumps(a) for a in row["aliases"])
        entries.append(
            "  {\n"
            f"    id: {json.dumps(row['id'])},\n"
            f"    aliases: [{aliases}],\n"
            f"    firstSceneChapter: {row['first_scene_chapter']},\n"
            f"    load: () => import({json.dumps(row['import_path'])}),\n"
            "  },"
        )
    body = "\n".join(entries)
    return (
        "/**\n"
        " * GENERATED — DO NOT EDIT.\n"
        " *\n"
        " * Emitted by scripts/sync_story_simulation_pack.py (via\n"
        " * scripts/story_pack_registry.py) from the synced pack artifacts in\n"
        " * data/generated/. The literal import() paths are load-bearing: they are\n"
        " * how Next emits one optional chunk per signed pack, which is why this\n"
        " * registry is a generated source file instead of runtime data.\n"
        " * check_story_simulations.py fails if this file drifts from the artifacts.\n"
        " */\n"
        "\n"
        "export const GENERATED_PACKS = [\n"
        f"{body}\n"
        "] as const; // sorted firstSceneChapter DESC — the newest saga owns the globe\n"
        "\n"
        'export type GeneratedPackId = (typeof GENERATED_PACKS)[number]["id"];\n'
    )


def emit() -> bool:
    """Write the registry. Returns True when the file changed."""
    content = render_ts(derive_rows())
    if REGISTRY_TS.is_file() and REGISTRY_TS.read_text() == content:
        return False
    REGISTRY_TS.write_text(content)
    return True
