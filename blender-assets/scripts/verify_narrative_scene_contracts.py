#!/usr/bin/env python3
"""Verify the narrative contract batch and its non-negotiable topology rules."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def read(contract_id: str) -> dict:
    return json.loads((CONTRACTS / f"{contract_id}.visual.json").read_text(encoding="utf-8"))


def component_ids(contract: dict) -> set[str]:
    return {item["id"] for item in contract["identity"]["components"]}


def main() -> int:
    index = json.loads((CONTRACTS / "narrative-scene-index.json").read_text(encoding="utf-8"))
    expected = {
        "conomi-arlong-park",
        "arabasta-kingdom",
        "cactus-island-whisky-peak",
        "dressrosa-green-bit",
        "zou-zunesha",
        "amazon-lily",
        "mary-geoise-red-line",
        "sabaody-grove-network",
        "skypiea-sky-system",
        "loguetown-roger-execution",
        "water-7-sea-train-network",
        "reverse-mountain-twin-cape-voyage",
    }
    assert index["contract_count"] == 12
    assert {item["id"] for item in index["contracts"]} == expected

    contracts = {contract_id: read(contract_id) for contract_id in expected}
    for contract in contracts.values():
        assert contract["schema_version"] == 2
        assert contract["topology"]["exact_distances"] == "unknown"
        assert contract["coordinate_policy"]["local_topology"].startswith("Build only from cited")
        assert contract["chapter_logic"]["temporal_variants"]
        assert contract["chapter_logic"]["event_scenes"]
        assert contract["visual_program"]["must_show"]
        assert contract["visual_program"]["must_not_show"]
        assert len(contract["evidence"]) == 5
        assert all(len(item["sha256"]) == 64 for item in contract["evidence"])

    assert {"green-bit-iron-bridge", "kings-plateau", "dressrosa-royal-palace"} <= component_ids(contracts["dressrosa-green-bit"])
    assert {"zunesha", "zunesha-legs", "zunesha-trunk"} <= component_ids(contracts["zou-zunesha"])
    assert "yarukiman-mangroves" in component_ids(contracts["sabaody-grove-network"])
    assert {"angel-island", "upper-yard", "giant-jack", "golden-belfry-cloud"} <= component_ids(contracts["skypiea-sky-system"])
    assert "execution-platform" in component_ids(contracts["loguetown-roger-execution"])

    amazon = contracts["amazon-lily"]
    assert any("whole-island serpent" in rule for rule in amazon["visual_program"]["must_not_show"])

    train = contracts["water-7-sea-train-network"]
    assert train["entity_type"] == "sea_train_route_network"
    assert set(train["route_network"]["known_terminals"]) == {
        "water-7", "enies-lobby", "pucci", "st-poplar", "san-faldo"
    }
    assert train["route_network"]["track_elevation"] == "just_below_ocean_surface"
    assert {"puffing-tom", "rocketman", "puffing-ice", "subsurface-sea-rails"} <= component_ids(train)

    reverse_mountain = contracts["reverse-mountain-twin-cape-voyage"]
    assert {"going-merry", "laboon-unidentified", "laboon", "crocus"} <= component_ids(reverse_mountain)
    whirlpool = next(item for item in reverse_mountain["identity"]["components"] if item["id"] == "local-whirlpool-emitter")
    assert whirlpool["verification"] == "chapter_to_verify"
    assert whirlpool["default_hidden"] is True

    print("12 narrative scene contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
