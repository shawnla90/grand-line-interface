#!/usr/bin/env python3
"""Read-only structural and chapter-gate verifier for Paradise gap batch A."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BATCH_ID = "paradise-gap-batch-a"
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO_ROOT / "blender-assets" / "contracts"
EVIDENCE_PATH = REPO_ROOT / "blender-assets" / "research" / f"{BATCH_ID}-evidence.json"

EXPECTED: dict[str, dict[str, Any]] = {
    f"{BATCH_ID}-little-garden.visual.json": {
        "slug": "little-garden",
        "base_gate": 115,
        "safe_gate": 118,
        "local_gate": 114,
        "atlas_anchor": [-118.6519, -5.3635],
    },
    f"{BATCH_ID}-drum-island.visual.json": {
        "slug": "drum-island",
        "base_gate": 132,
        "safe_gate": 153,
        "local_gate": 132,
        "atlas_anchor": [-108.7954, -6.3428],
    },
    f"{BATCH_ID}-jaya-upper-yard.visual.json": {
        "slug": "jaya",
        "base_gate": 222,
        "safe_gate": 253,
        "local_gate": 222,
        "atlas_anchor": [-96.4286, 6.9118],
    },
    f"{BATCH_ID}-long-ring-long-land.visual.json": {
        "slug": "long-ring-long-land",
        "base_gate": 304,
        "safe_gate": 305,
        "local_gate": 304,
        "atlas_anchor": [-83.0667, -2.0718],
    },
    f"{BATCH_ID}-thriller-bark.visual.json": {
        "slug": "thriller-bark",
        "base_gate": 443,
        "safe_gate": 449,
        "local_gate": 442,
        "atlas_anchor": [-57.5, 1.8],
    },
}

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "batch_id",
    "id",
    "label",
    "entity_type",
    "contract_status",
    "identity",
    "topology",
    "chapter_logic",
    "proposed_local_scene_layout",
    "unreal_runtime_reuse",
    "coordinate_policy",
    "integration_contract",
    "evidence",
    "unresolved",
}


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: cannot read valid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)}: JSON root must be an object")
        return {}
    return value


def local_canon_records(errors: list[str]) -> dict[str, dict[str, Any]]:
    canon_path = REPO_ROOT / "data" / "canon.json"
    canon = load_json(canon_path, errors)
    islands = canon.get("islands", [])
    if not isinstance(islands, list):
        errors.append("data/canon.json: islands must be an array")
        return {}
    return {
        row.get("slug"): row
        for row in islands
        if isinstance(row, dict) and row.get("slug") in {spec["slug"] for spec in EXPECTED.values()}
    }


def validate_sources(label: str, sources: Any, errors: list[str]) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label}: sources must be a non-empty array")
        return
    for source in sources:
        if not isinstance(source, str):
            errors.append(f"{label}: source must be a string: {source!r}")
            continue
        if source.startswith("https://"):
            continue
        local_path = source.split("#", 1)[0]
        if local_path not in {"data/canon.json", "canon/islands.extra.json"}:
            errors.append(f"{label}: unsupported source form: {source}")


def validate_contract(
    path: Path,
    spec: dict[str, Any],
    canon_rows: dict[str, dict[str, Any]],
    ledger_claim_ids: set[str],
    errors: list[str],
) -> tuple[str | None, int]:
    data = load_json(path, errors)
    if not data:
        return None, 0

    label = str(path.relative_to(REPO_ROOT))
    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        errors.append(f"{label}: missing top-level keys: {', '.join(missing)}")
    if data.get("schema_version") != 2:
        errors.append(f"{label}: schema_version must be 2")
    if data.get("batch_id") != BATCH_ID:
        errors.append(f"{label}: batch_id must be {BATCH_ID}")
    if data.get("contract_status") != "ready_for_blender_blockout_unregistered":
        errors.append(f"{label}: contract_status must remain unregistered blockout-ready")

    identity = data.get("identity", {})
    anchor = identity.get("anchor", {}) if isinstance(identity, dict) else {}
    slug = anchor.get("slug")
    if slug != spec["slug"]:
        errors.append(f"{label}: expected slug {spec['slug']}, got {slug!r}")
    if anchor.get("local_debut_chapter") != spec["local_gate"]:
        errors.append(f"{label}: local debut drifted from data/canon.json")
    if anchor.get("verified_visual_reveal_chapter") != spec["base_gate"]:
        errors.append(f"{label}: verified visual gate must be {spec['base_gate']}")
    atlas_anchor = anchor.get("atlas_anchor", {})
    actual_point = [atlas_anchor.get("lng"), atlas_anchor.get("lat")] if isinstance(atlas_anchor, dict) else None
    if actual_point != spec["atlas_anchor"]:
        errors.append(f"{label}: atlas anchor must match the local route record")

    canon_row = canon_rows.get(spec["slug"])
    if not canon_row:
        errors.append(f"{label}: local canon row not found for {spec['slug']}")
    else:
        if canon_row.get("debut_chapter") != spec["local_gate"]:
            errors.append(f"{label}: expected local debut {spec['local_gate']}, data/canon.json has {canon_row.get('debut_chapter')}")
        if [canon_row.get("lng"), canon_row.get("lat")] != spec["atlas_anchor"]:
            errors.append(f"{label}: expected atlas point does not match data/canon.json")

    chapter_logic = data.get("chapter_logic", {})
    if chapter_logic.get("base_reveal_chapter") != spec["base_gate"]:
        errors.append(f"{label}: base_reveal_chapter must be {spec['base_gate']}")
    if chapter_logic.get("safe_full_scene_chapter") != spec["safe_gate"]:
        errors.append(f"{label}: safe_full_scene_chapter must be {spec['safe_gate']}")
    if not chapter_logic.get("unknown_gate_rule"):
        errors.append(f"{label}: missing unknown_gate_rule")

    components = identity.get("components", []) if isinstance(identity, dict) else []
    component_ids: set[str] = set()
    if not isinstance(components, list) or not components:
        errors.append(f"{label}: components must be a non-empty array")
        components = []
    for component in components:
        if not isinstance(component, dict):
            errors.append(f"{label}: component is not an object")
            continue
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id:
            errors.append(f"{label}: component missing id")
            continue
        if component_id in component_ids:
            errors.append(f"{label}: duplicate component id {component_id}")
        component_ids.add(component_id)
        reveal = component.get("reveal_chapter")
        verification = component.get("verification")
        if reveal is not None and (not isinstance(reveal, (int, float)) or reveal < spec["base_gate"]):
            errors.append(f"{label}: {component_id} has unsafe reveal_chapter {reveal!r}")
        if verification == "chapter_to_verify":
            if reveal is not None or component.get("default_hidden") is not True:
                errors.append(f"{label}: unresolved {component_id} must have null reveal_chapter and default_hidden=true")
        if reveal is None and component.get("default_hidden") is not True:
            errors.append(f"{label}: ungated {component_id} must remain default_hidden")

    integration = data.get("integration_contract", {})
    if integration.get("registration_status") != "not_registered_by_this_lane":
        errors.append(f"{label}: registration_status must remain not_registered_by_this_lane")
    if "runtime_glb" in integration or "fallback" in integration:
        errors.append(f"{label}: only proposed_runtime_glb/proposed_fallback may appear in this contract-only lane")
    if not integration.get("proposed_runtime_glb") or not integration.get("proposed_fallback"):
        errors.append(f"{label}: proposed integration handoff paths are required")

    evidence = data.get("evidence", {})
    if evidence.get("ledger") != f"research/{BATCH_ID}-evidence.json":
        errors.append(f"{label}: evidence ledger path is incorrect")
    claim_ids = evidence.get("claim_ids", [])
    if not isinstance(claim_ids, list) or not claim_ids:
        errors.append(f"{label}: claim_ids must be a non-empty array")
    else:
        unknown = sorted(set(claim_ids) - ledger_claim_ids)
        if unknown:
            errors.append(f"{label}: claim ids missing from ledger: {', '.join(unknown)}")
    validate_sources(label, evidence.get("sources"), errors)

    if not isinstance(data.get("unresolved"), list) or not data["unresolved"]:
        errors.append(f"{label}: unresolved geometry list must not be empty")
    topology = data.get("topology", {})
    for key in ("verified_relationships", "interpolated_relationships", "transformation_policy"):
        if not topology.get(key):
            errors.append(f"{label}: topology.{key} is required")
    layout = data.get("proposed_local_scene_layout", {})
    if not layout.get("zones") or not layout.get("excluded_from_scene"):
        errors.append(f"{label}: local scene zones and exclusions are required")
    reuse = data.get("unreal_runtime_reuse", {})
    for key in ("reusable_modules", "unreal_notes", "map_runtime_notes"):
        if not reuse.get(key):
            errors.append(f"{label}: unreal_runtime_reuse.{key} is required")

    return data.get("id"), len(components)


def validate_special_boundaries(contracts: dict[str, dict[str, Any]], errors: list[str]) -> None:
    jaya = contracts[f"{BATCH_ID}-jaya-upper-yard.visual.json"]
    jaya_integration = jaya.get("integration_contract", {})
    external = jaya_integration.get("external_asset_reference", {})
    if external.get("system_id") != "skypiea-sky-system" or external.get("policy") != "reference_only_no_geometry_duplication":
        errors.append("Jaya: Upper Yard must be an external skypiea-sky-system reference with no geometry duplication")

    long_ring = contracts[f"{BATCH_ID}-long-ring-long-land.visual.json"]
    annual = next(
        (item for item in long_ring.get("identity", {}).get("components", []) if item.get("id") == "annual-low-tide-land-bridge-overlay"),
        {},
    )
    if annual.get("default_hidden") is not True or annual.get("classification") != "referenced_geographic_cycle":
        errors.append("Long Ring Long Land: annual low tide must remain a hidden explanatory geographic cycle")

    thriller = contracts[f"{BATCH_ID}-thriller-bark.visual.json"]
    if thriller.get("entity_type") != "chapter-gated mobile ship-island geographic system":
        errors.append("Thriller Bark: entity_type must remain a mobile ship-island system")
    coordinate_policy = thriller.get("coordinate_policy", {})
    if coordinate_policy.get("mobility_policy") != "moving_vessel_local_frame":
        errors.append("Thriller Bark: coordinate policy must use a moving vessel local frame")
    integration = thriller.get("integration_contract", {})
    if integration.get("mobility_policy") != "Load at story-scene transform; any drift applies to TB_SHIP_ROOT and all descendants.":
        errors.append("Thriller Bark: runtime mobility policy must preserve the single moving root")


def main() -> int:
    errors: list[str] = []
    actual_paths = sorted(CONTRACT_DIR.glob(f"{BATCH_ID}-*.visual.json"))
    actual_names = {path.name for path in actual_paths}
    expected_names = set(EXPECTED)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        if missing:
            errors.append(f"missing contracts: {', '.join(missing)}")
        if extra:
            errors.append(f"unexpected batch contracts: {', '.join(extra)}")

    ledger = load_json(EVIDENCE_PATH, errors)
    if ledger.get("id") != f"{BATCH_ID}-evidence":
        errors.append("evidence ledger id is incorrect")
    claims = ledger.get("claims", [])
    ledger_claim_ids = {
        claim.get("id") for claim in claims if isinstance(claim, dict) and isinstance(claim.get("id"), str)
    }
    if len(ledger_claim_ids) != 20 or len(claims) != 20:
        errors.append(f"evidence ledger must contain 20 unique claims, found {len(ledger_claim_ids)} unique / {len(claims)} total")
    for claim in claims:
        if isinstance(claim, dict):
            validate_sources(f"evidence claim {claim.get('id', '<missing-id>')}", claim.get("sources"), errors)

    canon_rows = local_canon_records(errors)
    seen_ids: set[str] = set()
    component_total = 0
    parsed_contracts: dict[str, dict[str, Any]] = {}
    for name, spec in EXPECTED.items():
        path = CONTRACT_DIR / name
        if not path.exists():
            continue
        parsed_contracts[name] = load_json(path, errors)
        contract_id, component_count = validate_contract(path, spec, canon_rows, ledger_claim_ids, errors)
        component_total += component_count
        if contract_id in seen_ids:
            errors.append(f"duplicate contract id: {contract_id}")
        if contract_id:
            seen_ids.add(contract_id)

    if set(parsed_contracts) == expected_names:
        validate_special_boundaries(parsed_contracts, errors)

    if errors:
        print(f"FAIL {BATCH_ID}: {len(errors)} issue(s)", file=sys.stderr)
        for issue in errors:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(
        f"PASS {BATCH_ID}: {len(parsed_contracts)} contracts, "
        f"{component_total} gated components, {len(ledger_claim_ids)} evidence claims; "
        "Jaya external-reference and Thriller Bark mobility boundaries enforced."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
