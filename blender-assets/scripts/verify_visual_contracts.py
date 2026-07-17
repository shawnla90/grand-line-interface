#!/usr/bin/env python3
"""Reject visual contracts that collapse systems or leak guessed geography."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(name: str):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def main() -> int:
    totto = read("totto-land.visual.json")
    tarai = read("world-government-tarai-system.visual.json")

    assert totto["entity_type"] == "archipelago_system"
    assert totto["identity"]["central"]["slug"] == "whole-cake-island"
    assert totto["identity"]["subsidiary_count"] == 34
    subsidiary_slugs = {item["slug"] for item in totto["identity"]["subsidiaries"]}
    assert {"cacao-island", "cheese-island", "nuts-island"} <= subsidiary_slugs
    assert totto["api_coverage"]["classification_repairs"]

    assert tarai["entity_type"] == "connected_world_structure"
    component_slugs = {item["slug"] for item in tarai["identity"]["components"]}
    assert component_slugs == {
        "enies-lobby",
        "impel-down",
        "marineford",
        "gates-of-justice",
        "tarai-current",
    }
    assert tarai["temporal_logic"]["state_change_chapter"] == 598
    assert len(tarai["identity"]["relationships"]) >= 5

    for contract in (totto, tarai):
        assert contract["evidence"]
        for item in contract["evidence"]:
            assert len(item["sha256"]) == 64
        assert contract["topology"]["exact_distances"] == "unknown"

    print("visual contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
