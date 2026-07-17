#!/usr/bin/env python3
"""sync_scenes.py — join the Blender track's narrative contracts into one
app-owned artifact. MACHINE-OWNED.

THE ASSET WORKSPACE IS READ-ONLY TO THIS REPO'S APP. blender-assets/ is Codex's;
we read it and never write it, and that is asserted in code rather than in prose
(assert_not_asset_workspace). Nothing here copies a .blend, a render or a GLB —
the runtime manifest is the integration boundary, and none of these 11 scenes
has reached it.

WHY AN ARTIFACT AND NOT A DIRECT READ. The contracts live in-repo (Codex commits
them), so the app COULD read them at request time. It should not: the useful
answer needs three files joined (the index, the queue, the blockout manifest),
the join has rules worth writing once, and every other generated input in this
project is a committed artifact validated at build time. data/generated/ is
exactly the shelf this belongs on — beside art_manifest.json and islands.json —
and canon/ is the wrong one, because canon/ is hand-authored and
assert_not_canon() exists to keep scripts out of it.

THE INDEX IS THE ONLY DOOR. Never glob contracts/*.visual.json: totto-land and
world-government-tarai-system are also schema_version 2 but are NOT v2 narrative
scenes (no relationships, no chapter_logic — the latter has temporal_logic
instead — and their entity_types are not in the enum). A glob picks them up and
validation dies on data that was never claiming to be this shape.

Inputs   blender-assets/contracts/narrative-scene-index.json   (the 11)
         blender-assets/contracts/*.visual.json                (via the index)
         blender-assets/queue/asset-requests.json              (integration state)
         blender-assets/manifests/narrative-blockouts.json     (runtime_export)

Output   data/generated/narrative_scenes.json

Run: python3 scripts/sync_scenes.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "blender-assets"
OUT = ROOT / "data" / "generated" / "narrative_scenes.json"

ENTITY_TYPES = {
    "nested_landmark_compound", "kingdom_region_system", "island_town_system",
    "island_bridge_system", "moving_world_entity", "mountain_city_system",
    "vertical_political_world_structure", "mangrove_grove_network",
    "sky_archipelago_system", "city_landmark_event_system", "sea_train_route_network",
}
CONTRACT_STATUS = {"research_hold", "ready_for_system_sketch", "ready_for_blender_blockout"}
VERIFICATION = {"verified", "chapter_to_verify"}


class DataError(Exception):
    """A row we refuse to guess at."""


def assert_not_asset_workspace(path: Path) -> None:
    """blender-assets/ belongs to the Blender track. This script READS it.

    The mirror of normalize.py's assert_not_canon(), and for the same reason: a
    boundary that lives only in a README is a boundary that gets crossed at 2am.
    """
    try:
        path.resolve().relative_to(ASSETS.resolve())
    except ValueError:
        return
    raise RuntimeError(
        f"ARCHITECTURE VIOLATION: sync_scenes.py tried to write into blender-assets/ "
        f"({path}). That workspace is the asset track's. This script reads it and "
        f"nothing else."
    )


def write_json(path: Path, payload) -> None:
    assert_not_asset_workspace(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path: Path):
    if not path.exists():
        raise DataError(f"missing input: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(scene: dict, path: str) -> None:
    """Mirror the contract's own schema. Tolerant where the schema is (it has no
    additionalProperties:false, and every real file carries priority/topology/
    api_coverage, which its `properties` never mentions); strict where the
    VALUES are enumerated."""
    for k in ("schema_version", "id", "label", "entity_type", "contract_status",
              "identity", "relationships", "chapter_logic", "visual_program", "evidence"):
        if k not in scene:
            raise DataError(f"{path}: required key {k!r} is missing")
    if scene["schema_version"] != 2:
        raise DataError(f"{path}: schema_version {scene['schema_version']} — this reads v2 only")
    if scene["entity_type"] not in ENTITY_TYPES:
        raise DataError(f"{path}: entity_type {scene['entity_type']!r} is not one of the 11")
    if scene["contract_status"] not in CONTRACT_STATUS:
        raise DataError(f"{path}: contract_status {scene['contract_status']!r}")
    if not scene["evidence"]:
        raise DataError(f"{path}: evidence is empty — a contract with no receipts")

    cl = scene["chapter_logic"]
    for k in ("base_reveal_chapter", "temporal_variants", "event_scenes"):
        if k not in cl:
            raise DataError(f"{path}: chapter_logic.{k} is missing")
    for v in cl["temporal_variants"]:
        if v.get("verification") and v["verification"] not in VERIFICATION:
            raise DataError(f"{path}: variant {v['id']}: verification {v['verification']!r}")
        # The rule that makes gate_unverified meaningful, asserted rather than
        # assumed: in every contract today, chapter_to_verify co-occurs with a
        # null reveal chapter. If that ever stops being true, the resolver's
        # two branches have quietly become one.
        if v.get("verification") == "chapter_to_verify" and v.get("reveal_chapter") is not None:
            raise DataError(
                f"{path}: variant {v['id']} is chapter_to_verify AND carries reveal_chapter "
                f"{v['reveal_chapter']}. Those mean opposite things; the app gates on the pair."
            )
    for e in cl["event_scenes"]:
        if not 1 <= e["importance"] <= 3:
            raise DataError(f"{path}: event {e['id']}: importance {e['importance']} outside 1..3")


def main() -> int:
    index = load(ASSETS / "contracts" / "narrative-scene-index.json")
    queue = {a["id"]: a for a in load(ASSETS / "queue" / "asset-requests.json")["assets"]}
    blockouts = {b["id"]: b for b in load(ASSETS / "manifests" / "narrative-blockouts.json")["assets"]}

    scenes = []
    evidence_checked = 0
    drift: dict[str, dict] = {}
    for row in index["contracts"]:
        path = row["path"]
        scene = load(ASSETS / path)
        validate(scene, path)
        if scene["id"] != row["id"]:
            raise DataError(f"{path}: id {scene['id']!r} disagrees with the index ({row['id']!r})")

        # The evidence rows pointing INTO this repo are a free drift detector: the
        # contract recorded a sha256 of our data, so a mismatch means the asset
        # track built against an atlas we have since changed.
        #
        # A WARNING, not an error, and the distinction is the whole judgement.
        # The two tracks move independently — this repo's canon changes on most
        # commits — so failing here would mean the app cannot build whenever the
        # tracks are one commit out of step, which is nearly always. Drift is
        # also not corruption: a contract's claims about ITS OWN scene do not
        # stop being true because we added an island somewhere else. (The first
        # run of this script proved the point: it fired on
        # canon/islands.coords.json, which moved in OUR commit adding Thriller
        # Bark, and not one contract mentions Thriller Bark.)
        #
        # What matters is that it is never SILENT. It lands in the artifact's
        # warnings, prints loudly here, and check_scenes reports it — so the
        # asset track knows to rebuild, and nobody discovers it by reading a
        # stale anchor six months from now.
        for ev in scene["evidence"]:
            if ev.get("ownership") != "atlas_read_only":
                continue
            p = Path(ev["path"])
            if not p.is_absolute():
                p = ROOT / p
            if not p.exists():
                raise DataError(f"{path}: evidence names {ev['path']}, which is not on disk")
            got = sha256(p)
            if got != ev["sha256"]:
                rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
                drift.setdefault(rel, {"was": ev["sha256"], "now": got, "scenes": []})
                drift[rel]["scenes"].append(scene["id"])
            else:
                evidence_checked += 1

        q = queue.get(row["id"])
        b = blockouts.get(row["id"])
        if b and sha256(ASSETS / b["contract"]) != b["contract_sha256"]:
            raise DataError(
                f"{row['id']}: the blockout manifest was built against a different version "
                f"of {b['contract']} than the one on disk."
            )

        scenes.append({
            "id": scene["id"],
            "label": scene["label"],
            "entity_type": scene["entity_type"],
            "contract_status": scene["contract_status"],
            "priority": row.get("priority"),
            # `state` — the index's own key. NOT `status`.
            "index_state": row["state"],
            "identity": scene["identity"],
            "relationships": scene["relationships"],
            "chapter_logic": scene["chapter_logic"],
            "route_network": scene.get("route_network"),
            "topology": scene.get("topology"),
            "unresolved": scene.get("unresolved", []),
            "visual_program": scene["visual_program"],
            "evidence": scene["evidence"],
            # The join. integration_ready is a QUEUE property and never a scene
            # one — resolve it here, once, rather than letting the app guess.
            "queue": {
                "state": q["state"] if q else None,
                "kind": q.get("kind") if q else None,
                "next": q.get("next") if q else None,
                "replaced_as_integration_unit_by": (q or {}).get("replaced_as_integration_unit_by"),
            },
            "blockout": {
                "exists": b is not None,
                "runtime_export": b["runtime_export"] if b else False,
                "maturity": b.get("maturity") if b else None,
            },
            "source_ref": f"blender-assets/{path}",
        })

    ready = [s["id"] for s in scenes if s["queue"]["state"] == "integration_ready"]
    warnings = []
    for f, d in sorted(drift.items()):
        warnings.append(
            f"EVIDENCE DRIFT: {len(d['scenes'])} contracts were built against {f} at "
            f"{d['was'][:12]}; it is now {d['now'][:12]}. Their claims about their own "
            f"scenes are unaffected, but any atlas_anchor derived from that file is stale. "
            f"The asset track should re-run scripts/build_narrative_scene_contracts.py."
        )
    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/sync_scenes.py",
            "source": "blender-assets/ (read-only; owned by the Blender asset track)",
            "warnings": warnings,
            "note": (
                "Joined from the narrative-scene INDEX (never a glob — two other "
                "schema_version-2 contracts are not v2 narrative scenes). integration_ready "
                "is a queue property, joined here; it is never a field on a scene."
            ),
            "counts": {
                "scenes": len(scenes),
                "with_blockout": sum(1 for s in scenes if s["blockout"]["exists"]),
                "runtime_exportable": sum(1 for s in scenes if s["blockout"]["runtime_export"]),
                "integration_ready": len(ready),
                "evidence_sha256_checked": evidence_checked,
            },
        },
        "scenes": scenes,
    }
    write_json(OUT, payload)

    c = payload["_meta"]["counts"]
    print(f"wrote {OUT.relative_to(ROOT)}")
    for k, v in c.items():
        print(f"  {k:28} {v}")
    for w in warnings:
        print(f"\n  WARNING: {w}")
    if not ready:
        print("\n  0 scenes are integration_ready — the app can render none of them, which is")
        print("  the correct answer today. asset_not_ready is not a bug; it is the gate.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as e:
        print(f"\nsync_scenes: {e}\n", file=sys.stderr)
        sys.exit(1)
