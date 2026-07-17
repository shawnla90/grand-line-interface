#!/usr/bin/env python3
"""check_simulations.py — the guard suite for the East Blue 2.5D pack.

Assertions about the DATA the app ships, in the check_canon.py mold: every check
exists because a specific way of being wrong would reach a reader who has not
gotten to that chapter yet, or would put unsigned bytes on their screen.

Run: python3 scripts/check_simulations.py
Exit 0 = the simulation artifact is shippable. Exit 1 = it is not.
"""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIM_JSON = ROOT / "data" / "generated" / "east_blue_simulations.json"
CANON_JSON = ROOT / "data" / "canon.json"
MANIFEST = ROOT / "blender-assets" / "manifests" / "east-blue-2d.json"
ANCHORS = ROOT / "canon" / "east_blue_scene_anchors.json"
ATLAS_DIR = ROOT / "public" / "art" / "east-blue-2d"
RUNTIME_ASSETS = ROOT / "data" / "generated" / "runtime_assets.json"

# The two v1 holes, pinned BY NAME. If a third scene ever lands refused, or one
# of these two quietly ships, that is a human decision — not drift.
ART_PARTIAL_IDS = {"zoro-joins-at-shells-town", "smoker-dragon-storm-escape"}

results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(ctx):
            try:
                detail = fn(ctx) or "ok"
                results.append((name, True, detail))
            except AssertionError as exc:
                results.append((name, False, str(exc)))
        run.__name__ = name
        return run
    return deco


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@check("atlases_are_signed_bytes")
def atlases_are_signed_bytes(ctx):
    """Every atlas under public/ matches the manifest's sha256, and nothing
    lives there that the manifest did not sign."""
    manifest = ctx["manifest"]
    signed = {c["id"]: c["atlas"]["sha256"] for c in manifest["characters"]}
    on_disk = {p.parent.name: p for p in ATLAS_DIR.glob("*/atlas.png")}
    assert set(on_disk) == set(signed), (
        f"public/art/east-blue-2d disagrees with the manifest: "
        f"unsigned={sorted(set(on_disk) - set(signed))} missing={sorted(set(signed) - set(on_disk))}"
    )
    for cid, p in on_disk.items():
        assert sha256(p) == signed[cid], f"{cid}: served atlas bytes do not match the manifest's sha256"
    strays = [p.name for p in ATLAS_DIR.rglob("*") if p.is_file() and p.name != "atlas.png"]
    assert not strays, f"unsigned files in the served dir: {strays}"
    return f"{len(on_disk)} atlases, all signed"


@check("shells_town_stays_dark")
def shells_town_stays_dark(ctx):
    """The tripwire. Exactly the 12 runtime_ready scenes ship and exactly the 2
    art_partial scenes are refused — pinned by id, disjoint. The scraper-mistake
    this catches: someone 'fixes' the refusal by editing the artifact instead of
    shipping Morgan/Koby art through the signed pipeline."""
    sim = ctx["sim"]
    shipped = {s["id"] for s in sim["scenes"]}
    refused = {r["id"] for r in sim["refused"]}
    assert refused == ART_PARTIAL_IDS, f"refused set changed: {sorted(refused)} != {sorted(ART_PARTIAL_IDS)}"
    assert not (shipped & ART_PARTIAL_IDS), f"art_partial scene shipped: {sorted(shipped & ART_PARTIAL_IDS)}"
    assert len(shipped) == 12, f"{len(shipped)} scenes shipped, expected 12"
    for r in sim["refused"]:
        assert r["missing_assets"], f"{r['id']}: refused without naming its missing assets"
    return "12 shipped, 2 refused, disjoint"


@check("scene_gates_verified")
def scene_gates_verified(ctx):
    """Every shipped scene's chapter gate is verified and inside the pack span."""
    for s in ctx["sim"]["scenes"]:
        g = s["chapter_gate"]
        assert g.get("verification") == "verified", f"{s['id']}: gate not verified"
        assert 1 <= g["start"] <= g["end"] <= 100, f"{s['id']}: gate {g['start']}..{g['end']} out of range"
        assert g.get("source_url"), f"{s['id']}: gate has no source_url receipt"
    return "12 verified gates in 1..100"


@check("mihawk_scene_gate")
def mihawk_scene_gate(ctx):
    """The duel tripwire, pack edition — same mold as check_canon's
    mihawk_duel_test. The scene must gate on the DUEL (readable ch 43..52),
    never on the Baratie arc start. A gate of 42 means someone re-derived it
    from the arc table."""
    scene = next(s for s in ctx["sim"]["scenes"] if s["id"] == "baratie-zoro-vs-mihawk")
    g = scene["chapter_gate"]["start"]
    assert 42 < g <= 52, f"baratie-zoro-vs-mihawk gates at ch {g} — that is the arc, not the duel"
    cast = {a["asset_id"] for a in scene["actors"]}
    assert cast == {"roronoa-zoro", "dracule-mihawk"}, f"duel cast is {sorted(cast)}"
    return f"duel gates at ch {g} with both duelists"


@check("anchors_never_leak")
def anchors_never_leak(ctx):
    """Every shipped scene has exactly one anchor, every anchor resolves, and no
    anchor's own reveal calendar postdates the scene gate. Event anchors: the
    scene may not open before the event occurred. Island anchors: not before the
    island debuts. Literal anchors: hand-authored, must say so and must carry
    the NEEDS HUMAN VERIFICATION sentence."""
    anchors = ctx["anchors"]["anchors"]
    events = {e["slug"]: e for e in ctx["canon"]["events"]}
    islands = {i["slug"]: i for i in ctx["canon"]["islands"]}
    shipped = {s["id"]: s for s in ctx["sim"]["scenes"]}
    assert set(anchors) == set(shipped), (
        f"anchor table disagrees with shipped scenes: "
        f"unanchored={sorted(set(shipped) - set(anchors))} orphaned={sorted(set(anchors) - set(shipped))}"
    )
    kinds = {"event": 0, "island": 0, "literal": 0}
    for sid, a in anchors.items():
        gate = shipped[sid]["chapter_gate"]["start"]
        declared = [k for k in ("event", "island") if k in a] + (["literal"] if "lng" in a or "lat" in a else [])
        assert len(declared) == 1, f"{sid}: anchor declares {declared or 'nothing'}, needs exactly one kind"
        if "event" in a:
            ev = events.get(a["event"])
            assert ev, f"{sid}: anchor event {a['event']!r} is not a canon event"
            assert gate >= ev["occurred_chapter"], (
                f"{sid}: scene gate ch {gate} opens before its event "
                f"{a['event']!r} occurs at ch {ev['occurred_chapter']} — the scene would leak the event"
            )
            kinds["event"] += 1
        elif "island" in a:
            isl = islands.get(a["island"])
            assert isl, f"{sid}: anchor island {a['island']!r} is not a canon island"
            debut = isl.get("debut_chapter")
            assert debut is not None and gate >= debut, (
                f"{sid}: scene gate ch {gate} opens before island {a['island']!r} debuts at ch {debut}"
            )
            kinds["island"] += 1
        else:
            assert isinstance(a.get("lng"), (int, float)) and isinstance(a.get("lat"), (int, float)), (
                f"{sid}: literal anchor without both lng and lat"
            )
            note = a.get("note") or ""
            assert "NEEDS HUMAN VERIFICATION" in note and note.startswith("Hand-authored"), (
                f"{sid}: literal anchor must confess it is hand-authored and unverified"
            )
            kinds["literal"] += 1
        # The artifact's resolved coordinate must be the anchor's own — a scene
        # that drifted from its event's sea is a scene lying about geography.
        stamped = shipped[sid].get("anchor") or {}
        if "event" in a:
            ev = events[a["event"]]
            want = (ev["lng"], ev["lat"])
        elif "island" in a:
            isl = islands[a["island"]]
            want = (isl.get("lng"), isl.get("lat"))
        else:
            want = (a["lng"], a["lat"])
        got = (stamped.get("lng"), stamped.get("lat"))
        assert got == want, f"{sid}: artifact anchor {got} disagrees with the resolved source {want}"
    return f"{kinds['event']} event / {kinds['island']} island / {kinds['literal']} literal anchors, none leak, coords agree"


@check("keyframes_well_formed")
def keyframes_well_formed(ctx):
    """Every keyframe pose exists in its actor's atlas frames; times strictly
    ascend and stay inside the scene; FX events stay inside the scene."""
    assets = ctx["sim"]["assets"]
    n_kf = 0
    for s in ctx["sim"]["scenes"]:
        for actor in s["actors"]:
            frames = assets[actor["asset_id"]]["frames"]
            last = -1
            for kf in actor["keyframes"]:
                assert kf["pose"] in frames, f"{s['id']}/{actor['id']}: pose {kf['pose']!r} not in atlas"
                assert kf["t"] > last, f"{s['id']}/{actor['id']}: keyframe times not strictly ascending"
                assert kf["t"] <= s["duration_ms"], f"{s['id']}/{actor['id']}: t={kf['t']} beyond scene end"
                last = kf["t"]
                n_kf += 1
        for ev in s["events"]:
            assert 0 <= ev["t"] <= s["duration_ms"], f"{s['id']}: FX at t={ev['t']} outside the scene"
    return f"{n_kf} keyframes across 12 scenes"


@check("atlas_geometry")
def atlas_geometry(ctx):
    """Served atlases are exactly 1152x768 (the 3x2 grid of 384px cells the UV
    math in lib/simulation.ts hard-codes), and every frame table agrees."""
    for cid, asset in ctx["sim"]["assets"].items():
        p = ATLAS_DIR / cid / "atlas.png"
        b = p.read_bytes()
        assert b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR", f"{cid}: not a png"
        w, h = struct.unpack(">II", b[16:24])
        assert (w, h) == (1152, 768), f"{cid}: atlas is {w}x{h}, the UV math assumes 1152x768"
        g = asset["grid"]
        assert (g["columns"], g["rows"], g["cell_px"]) == (3, 2, 384), f"{cid}: grid {g}"
        for pose, f in asset["frames"].items():
            assert 0 <= f["col"] < 3 and 0 <= f["row"] < 2, f"{cid}/{pose}: cell ({f['col']},{f['row']}) off-grid"
    return "14 atlases at 1152x768, frames on-grid"


@check("sync_is_deterministic")
def sync_is_deterministic(ctx):
    """Re-running the sync produces byte-identical output. The artifact carries
    no timestamp by construction; this proves nothing else snuck in."""
    before = sha256(SIM_JSON)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_east_blue_2d.py")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"sync re-run failed: {proc.stderr.strip()[:200]}"
    assert sha256(SIM_JSON) == before, "sync re-run changed the artifact — a timestamp or nondeterminism snuck in"
    return "re-run byte-identical"


@check("superseded_glbs_stay_dead")
def superseded_glbs_stay_dead(ctx):
    """The three rigid-part encounter GLBs this pack supersedes must never be
    renderable runtime assets. They exist as motion studies only."""
    dead = set(ctx["sim"]["supersedes_visible_art"])
    assert dead, "manifest lost its supersedes_visible_art list"
    if RUNTIME_ASSETS.exists():
        runtime = json.loads(RUNTIME_ASSETS.read_text())
        live = {a["id"] for a in runtime.get("assets", [])}
        assert not (dead & live), f"superseded encounter art is renderable: {sorted(dead & live)}"
    return f"{len(dead)} superseded ids, none renderable"


CHECKS = [
    atlases_are_signed_bytes, shells_town_stays_dark, scene_gates_verified,
    mihawk_scene_gate, anchors_never_leak, keyframes_well_formed,
    atlas_geometry, sync_is_deterministic, superseded_glbs_stay_dead,
]


def main() -> int:
    ctx = {
        "sim": json.loads(SIM_JSON.read_text()),
        "canon": json.loads(CANON_JSON.read_text()),
        "manifest": json.loads(MANIFEST.read_text()),
        "anchors": json.loads(ANCHORS.read_text()),
    }
    for fn in CHECKS:
        fn(ctx)
    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  {mark}  {name:<{width}}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
