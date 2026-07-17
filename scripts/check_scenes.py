#!/usr/bin/env python3
"""check_scenes.py — the guard suite for the narrative scene registry.

A separate file from check_canon.py on purpose: that one makes assertions about
data/canon.json, the atlas's own artifact. This one is about a JOIN across
somebody else's workspace, and the two have different failure modes and
different owners.

Every check exists because a specific way of being wrong would either show a
reader an asset that is not finished, or quietly stop showing them one that is.

Run: python3 scripts/check_scenes.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "data" / "generated" / "narrative_scenes.json"
RUNTIME = ROOT / "data" / "generated" / "runtime_assets.json"
ASSETS = ROOT / "blender-assets"

ENTITY_TYPES = {
    "nested_landmark_compound", "kingdom_region_system", "island_town_system",
    "island_bridge_system", "moving_world_entity", "mountain_city_system",
    "vertical_political_world_structure", "mangrove_grove_network",
    "sky_archipelago_system", "city_landmark_event_system", "sea_train_route_network",
}
# The names that DO NOT EXIST in any contract. If one shows up in the artifact,
# somebody invented a field the asset track never agreed to, and the app is now
# describing a world of its own.
INVENTED = ["moving_anchor", "movement_model", "anchor_mode", "grove_count",
            "subregions", "landmarks", "station_type", "derived_schematic"]

results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(doc):
            try:
                results.append((name, True, fn(doc) or "ok"))
            except AssertionError as exc:
                results.append((name, False, str(exc)))
        return run
    return deco


def visibility(scene: dict, chapter: int) -> dict:
    """A faithful port of lib/scenes.ts::sceneVisibilityAt — the resolver the app
    actually uses. Kept in step by the checks below, which assert the SAME facts
    the TS is written to produce."""
    reasons = []
    cl = scene["chapter_logic"]
    base = cl["base_reveal_chapter"]
    if base is not None and base > chapter:
        reasons.append("chapter_locked")
    candidates = []
    for v in cl["temporal_variants"]:
        if v.get("verification") == "chapter_to_verify" or v["reveal_chapter"] is None:
            continue
        if v["reveal_chapter"] > chapter:
            continue
        candidates.append(v)
    state = None
    for v in candidates:  # array order + >= : a tie resolves to the LAST authored
        if state is None or v["reveal_chapter"] >= state["reveal_chapter"]:
            state = v
    if state is None and "chapter_locked" not in reasons:
        reasons.append("gate_unverified")
    if scene["queue"]["state"] != "integration_ready" or not scene["blockout"]["runtime_export"]:
        reasons.append("asset_not_ready")
    return {"visible": not reasons, "reasons": reasons, "state": state}


# ---------------------------------------------------------------------------
@check("registry_shape")
def registry_shape(doc):
    scenes = doc["scenes"]
    assert len(scenes) == 11, f"{len(scenes)} scenes; the index declares 11"
    for s in scenes:
        assert s["entity_type"] in ENTITY_TYPES, f"{s['id']}: entity_type {s['entity_type']!r}"
        assert "index_state" in s, f"{s['id']}: the index's key is `state` -> index_state"
        assert "status" not in s, f"{s['id']}: the index says `state`, never `status`"
        blob = json.dumps(s)
        for bad in INVENTED:
            assert f'"{bad}"' not in blob, (
                f"{s['id']}: the artifact contains {bad!r}, which exists in NO contract. "
                f"Either the asset track added it (update this list deliberately) or we "
                f"invented it (do not)."
            )
    return f"11 scenes, every entity_type known, no invented field names"


@check("integration_gate_holds")
def integration_gate_holds(doc):
    """The asset gate is not ours to open. Zero v2 scenes are integration_ready,
    and both blockouts are runtime_export:false — hard-asserted by the asset
    track's OWN verifier. If this check ever fails, an asset became renderable
    and somebody should decide that on purpose."""
    ready = [s["id"] for s in doc["scenes"] if s["queue"]["state"] == "integration_ready"]
    assert not ready, (
        f"{len(ready)} v2 narrative scenes now claim integration_ready ({ready}). Nothing is "
        f"wrong with that — but the app has never rendered one, so this is a decision, not a "
        f"detail. Wire it deliberately and then relax this check."
    )
    exportable = [s["id"] for s in doc["scenes"] if s["blockout"]["runtime_export"]]
    assert not exportable, f"blockouts now claim runtime_export: {exportable}"
    for s in doc["scenes"]:
        v = visibility(s, 1185)
        assert "asset_not_ready" in v["reasons"], (
            f"{s['id']} resolves without asset_not_ready at the last chapter"
        )
        assert not v["visible"], f"{s['id']} is VISIBLE — no asset backs it"
    return "all 11 resolve asset_not_ready at every chapter; two independent locks intact"


@check("replacement_join_is_not_loose")
def replacement_join_is_not_loose(doc):
    """skypiea-knock-up-stream IS integration_ready and is NOT skypiea-sky-system.
    A join on a fuzzy id — or on `replaced_as_integration_unit_by` in the wrong
    direction — would hand the sky system a readiness it does not have."""
    queue = {a["id"]: a for a in json.loads((ASSETS / "queue" / "asset-requests.json").read_text())["assets"]}
    assert queue["skypiea-knock-up-stream"]["state"] == "integration_ready"
    sky = next(s for s in doc["scenes"] if s["id"] == "skypiea-sky-system")
    assert sky["queue"]["state"] != "integration_ready", (
        "skypiea-sky-system inherited the Knock-Up Stream's readiness — the join is loose"
    )
    # the redirects the queue asks us to honour
    redirects = {a["id"]: a["replaced_as_integration_unit_by"]
                 for a in queue.values() if a.get("replaced_as_integration_unit_by")}
    ids = {s["id"] for s in doc["scenes"]}
    for old, new in redirects.items():
        assert old not in ids, f"{old!r} is a superseded study and must not be a scene"
    return f"{len(redirects)} superseded studies excluded; the Skypiea join stays honest"


@check("water_7_inversion")
def water_7_inversion(doc):
    """base_reveal_chapter (323) is LATER than the earliest variant (322). The
    base gates the place and the variants gate its state; the later of the two
    wins. Anyone "fixing" this by taking the min would open the scene a chapter
    early, so the inversion is asserted rather than trusted."""
    w7 = next(s for s in doc["scenes"] if s["id"] == "water-7-sea-train-network")
    base = w7["chapter_logic"]["base_reveal_chapter"]
    earliest = min(v["reveal_chapter"] for v in w7["chapter_logic"]["temporal_variants"]
                   if v["reveal_chapter"] is not None)
    assert base > earliest, (
        f"the inversion is gone (base {base} <= earliest variant {earliest}). If the asset "
        f"track fixed it upstream, delete this check; do not adjust the resolver to match."
    )
    assert "chapter_locked" in visibility(w7, 322)["reasons"], "ch322 should still be locked"
    assert "chapter_locked" not in visibility(w7, 323)["reasons"], "ch323 should be open"
    assert visibility(w7, 323)["state"]["id"] == "network-first-reveal"
    return f"base {base} > earliest variant {earliest}; locked at 322, open at 323"


@check("tiebreak_is_deterministic")
def tiebreak_is_deterministic(doc):
    """"Render the latest verified state whose reveal chapter is <= the reader
    chapter" is AMBIGUOUS: three scenes have two verified variants at the same
    chapter. Array order breaks the tie, so the answer must be stable — a set or
    a dict iteration order would make this flap between builds."""
    ties = 0
    for s in doc["scenes"]:
        seen: dict[int, list[str]] = {}
        for v in s["chapter_logic"]["temporal_variants"]:
            if v.get("verification") == "chapter_to_verify" or v["reveal_chapter"] is None:
                continue
            seen.setdefault(v["reveal_chapter"], []).append(v["id"])
        for ch, ids in seen.items():
            if len(ids) < 2:
                continue
            ties += 1
            got = visibility(s, ch)["state"]["id"]
            assert got == ids[-1], (
                f"{s['id']}: tie at ch{ch} between {ids} resolved to {got!r}; array order says "
                f"{ids[-1]!r}. The asset track wrote them in order and the later one is the "
                f"more specific state."
            )
    assert ties >= 3, f"only {ties} ties found; skypiea/zou/loguetown all have one"
    return f"{ties} same-chapter ties, each resolving to the last authored variant"


@check("unverified_gates_stay_dark")
def unverified_gates_stay_dark(doc):
    """The contracts' own unknown_gate_rule: "Do not render a chapter_to_verify
    state until its exact gate is confirmed." And the pairing that makes the
    reason meaningful: chapter_to_verify always co-occurs with a null chapter."""
    n = 0
    for s in doc["scenes"]:
        for v in s["chapter_logic"]["temporal_variants"] + s["chapter_logic"]["event_scenes"]:
            if v.get("verification") != "chapter_to_verify":
                continue
            n += 1
            assert v["reveal_chapter"] is None, (
                f"{s['id']}/{v['id']}: chapter_to_verify AND reveal_chapter "
                f"{v['reveal_chapter']} — those mean opposite things"
            )
        rule = s["chapter_logic"].get("unknown_gate_rule", "")
        assert "chapter_to_verify" in rule, f"{s['id']}: lost its unknown_gate_rule"
    assert n >= 14, f"only {n} chapter_to_verify gates; the corpus has 14+"
    return f"{n} unverified gates, every one with a null chapter, all withheld"


@check("event_landmarks_resolve")
def event_landmarks_resolve(doc):
    """An event points at a component by id. Edges may dangle (they name
    materials and other contracts) but an event's `landmark` is a real reference,
    and a broken one means the event can never be placed."""
    for s in doc["scenes"]:
        ids = {c["id"] for c in s["identity"]["components"]}
        for e in s["chapter_logic"]["event_scenes"]:
            assert e["landmark"] in ids, (
                f"{s['id']}: event {e['id']} names landmark {e['landmark']!r}, which is not a "
                f"component of this scene"
            )
    total = sum(len(s["chapter_logic"]["event_scenes"]) for s in doc["scenes"])
    return f"{total} event scenes, every landmark resolving to a real component"


@check("runtime_pilot_gate")
def runtime_pilot_gate(doc):
    """The two assets we DID wire. Skypiea renders; Wano must not — its own
    manifest says its chapter beats are proposed and unverified, and an asset
    being ready is a different question from its chapter being known."""
    if not RUNTIME.exists():
        raise AssertionError("data/generated/runtime_assets.json is missing — run sync_runtime_assets.py")
    r = json.loads(RUNTIME.read_text())
    by = {a["id"]: a for a in r["assets"]}
    assert r["_meta"]["feature_flag"] == "NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS", (
        "the flag name must come from the manifest, never be invented here"
    )
    sky = by.get("skypiea-knock-up-stream")
    assert sky and not sky["gate_unverified"], "the Skypiea beats should be verified"
    assert sky["chapter_beats"]["start"] == 235 and sky["chapter_beats"]["top"] == 237, (
        f"the asset's beats {sky['chapter_beats']} no longer match ASCENT in "
        f"components/skypiea.ts — the render and the ship would disagree"
    )
    wano = by.get("wano-waterfall-ascent")
    assert wano and wano["gate_unverified"], (
        "wano-waterfall-ascent is no longer gate_unverified. Its beats were 'proposed; exact "
        "waterfall climb beats need human verification'. If a human verified them, wire it "
        "deliberately."
    )
    assert not any(a["id"] in by for a in r["refused"]), "an asset is both copied and refused"
    return (f"{len(r['assets'])} sanctioned rasters; Skypiea's beats still match ASCENT; "
            f"Wano withheld as gate_unverified")


@check("artifact_is_reproducible")
def artifact_is_reproducible(doc):
    """The artifact is DERIVED. If it does not reproduce from the contracts, it
    has been hand-edited, and a hand-edited join is a lie with a timestamp."""
    before = ARTIFACT.read_text()
    subprocess.run([sys.executable, "scripts/sync_scenes.py"], cwd=ROOT,
                   capture_output=True, check=True)
    after = ARTIFACT.read_text()
    a, b = json.loads(before), json.loads(after)
    a["_meta"]["generated_at"] = b["_meta"]["generated_at"] = ""
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), (
        "narrative_scenes.json does not reproduce from blender-assets/ — it has drifted from "
        "its source, or somebody edited the artifact instead of the contract"
    )
    return "reproduces byte-for-byte from the in-repo contracts"


CHECKS = [registry_shape, integration_gate_holds, replacement_join_is_not_loose,
          water_7_inversion, tiebreak_is_deterministic, unverified_gates_stay_dark,
          event_landmarks_resolve, runtime_pilot_gate, artifact_is_reproducible]


def main() -> int:
    if not ARTIFACT.exists():
        print("data/generated/narrative_scenes.json is missing — run scripts/sync_scenes.py",
              file=sys.stderr)
        return 1
    doc = json.loads(ARTIFACT.read_text())
    for c in CHECKS:
        c(doc)

    width = max(len(n) for n, _, _ in results)
    print(f"\ncheck_scenes — {ARTIFACT.relative_to(ROOT)} "
          f"({ARTIFACT.stat().st_size:,} bytes)\n")
    failed = 0
    for name, ok, detail in results:
        if not ok:
            failed += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")

    for w in doc["_meta"].get("warnings", []):
        print(f"\n  WARNING: {w}")

    print()
    if failed:
        print(f"{failed}/{len(results)} CHECKS FAILED\n")
        return 1
    print(f"{len(results)}/{len(results)} checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
