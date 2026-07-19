#!/usr/bin/env python3
"""Focused validation for the standalone Punk Hazard runtime package."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
ASSET="punk-hazard-geographic-system"
MANIFEST=ROOT/"manifests/punk-hazard-runtime.json"
REQUIRED={
    "punk-hazard","burning-lands","fiery-sea","burning-lands-volcano",
    "melted-government-base","ice-lands","central-crater-lake","sea-channel",
    "ice-river","captured-ships-harbor","iceberg-choke","third-research-institute",
    "laboratory-industrial-system","first-second-institute-ruins",
    "climate-boundary-ambient","duel-memory-fx",
}
CLIPS={"punk_hazard_environment_cycle","punk_hazard_duel_memory_fx"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb(path: Path) -> dict:
    with path.open("rb") as handle:
        magic,version,declared=struct.unpack("<4sII",handle.read(12))
        assert magic==b"glTF" and version==2 and declared==path.stat().st_size
        length,kind=struct.unpack("<II",handle.read(8)); assert kind==0x4E4F534A
        return json.loads(handle.read(length).decode("utf-8").rstrip(" \t\r\n\x00"))


def png(path: Path) -> list[int]:
    data=path.read_bytes()[:26]
    assert data[:8]==b"\x89PNG\r\n\x1a\n" and data[12:16]==b"IHDR"
    assert data[25] in {4,6},f"{path}: no alpha channel"
    return list(struct.unpack(">II",data[16:24]))


def main() -> int:
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    contract=json.loads((ROOT/manifest["files"]["contract"]).read_text(encoding="utf-8"))
    assert manifest["id"]==ASSET and manifest["registration_status"]=="not_registered_by_this_lane"
    files={key:ROOT/value for key,value in manifest["files"].items() if key!="previews"}
    assert sha(files["contract"])==manifest["hashes"]["contract_sha256"]
    assert sha(files["research"])==manifest["hashes"]["research_sha256"]
    assert sha(files["blend"])==manifest["hashes"]["blend_sha256"]
    assert sha(files["glb"])==manifest["hashes"]["glb_sha256"]
    assert sha(files["model"])==manifest["hashes"]["model_sha256"]
    assert sha(files["fallback"])==manifest["hashes"]["fallback_sha256"]
    assert png(files["fallback"])==manifest["fallback"]["pixel_size"]
    for relative in manifest["files"]["previews"]:
        path=ROOT/relative
        assert sha(path)==manifest["hashes"]["preview_sha256"][path.name]
        png(path)
    doc=glb(files["glb"])
    tagged={}
    examples={}
    for node in doc.get("nodes",[]):
        extras=node.get("extras") or {}; cid=extras.get("component_id")
        if cid:
            tagged[cid]=tagged.get(cid,0)+1; examples.setdefault(cid,extras)
    assert REQUIRED<=set(tagged),f"missing tagged components: {sorted(REQUIRED-set(tagged))}"
    for gate in manifest["component_gates"]:
        if gate["id"] not in REQUIRED:
            continue
        assert gate["id"] in tagged
        extras=examples[gate["id"]]
        assert extras.get("reveal_chapter")==gate["reveal_chapter"]
        if gate.get("default_hidden"):
            assert extras.get("default_hidden") is True
    memory=examples["duel-memory-fx"]
    assert memory["gate_confidence"]=="verified_state_window"
    assert memory["classification"]=="referenced_historical_reconstruction"
    assert memory["historical_reference_only"] is True and memory["geography_transform"] is False
    assert memory["active_through_chapter"]==658.999
    for component in REQUIRED-{"duel-memory-fx"}:
        assert examples[component].get("default_hidden") is False, \
            f"{component}: ordinary reveal gate was made permanently hidden"
    actual={row.get("name") for row in doc.get("animations",[])}
    assert actual==CLIPS,f"clips {sorted(actual)} != {sorted(CLIPS)}"
    node_names=[row.get("name","").lower() for row in doc.get("nodes",[])]
    forbidden=("akainu","aokiji","sakazuki","kuzan","mannequin")
    assert not [name for name in node_names if any(token in name for token in forbidden)], \
        "historical duel character/mannequin node leaked into the geography asset"
    budget=contract["visual_program"]["runtime_budget"]
    assert files["glb"].stat().st_size<=budget["max_glb_bytes"]
    assert manifest["stats"]["triangles_input"]<=budget["target_triangles"]
    bounds=manifest["stats"].get("bounds_blender")
    assert bounds and all(bounds["max"][i]>bounds["min"][i] for i in range(3)), \
        "missing or degenerate runtime scale bounds"
    assert manifest["chapter_beats"]=={
        "pre_reveal_through":654,"base_reveal":655,"two_sided_reveal":657,
        "historical_cause_reveal":658,"compass_orientation":659,
        "crater_origin_reveal":661,"safe_full_scene":664,
    }
    print(f"PASS {ASSET}: {len(tagged)} component IDs, {manifest['stats']['triangles_input']} triangles, {files['glb'].stat().st_size} bytes")
    print("PASS clips: "+", ".join(sorted(actual)))
    print("PASS chapter gates: pre-reveal 654; arrival 655; split 657; history 658; orientation 659; crater origin 661; full 664")
    print("PASS standalone boundary: shared registries and app copies are not inputs or outputs")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
