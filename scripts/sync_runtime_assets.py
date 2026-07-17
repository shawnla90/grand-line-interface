#!/usr/bin/env python3
"""sync_runtime_assets.py — copy the SANCTIONED runtime assets into public/.
MACHINE-OWNED. Schema version 2.

THE MANIFEST IS THE BOUNDARY, NOT CHAT HISTORY. The asset track's WORKFLOW says
it in those words: "Claude Code reads the manifests and integrates only approved
assets behind chapter gates and a feature flag." So this script reads
manifests/runtime-3d.json, checks each asset's own queue state, and copies
nothing else. A human deciding an asset "looks done" is not an input here.

WHAT IT COPIES: the `glb` and the `fallback.path` of every model whose queue
state is `integration_ready` and whose bytes match the manifest's sha256 — the
16 validated models of the runtime batch.

WHAT IT REFUSES, and why the last one is the point of this file:

  - anything whose queue state is not `integration_ready`. A `scene_3d` or
    `study_only` entry is reviewable source, not permission.
  - anything whose bytes do not match the sha256 the manifest recorded. That is
    the asset track's signature on this exact file; we serve these bytes to a
    browser, so the signature is the gate and not a smell test.
  - ANY MODEL DECLARING A WITHHELD COMPONENT IT CANNOT EXPRESS.

That last rule exists because the batch contains real instances of it, and
nothing else catches them. The handoff's acceptance list says "A GLB node is
never rendered before its component gate", and runtime_policy.node_gate_policy
says to "read component_id, reveal_chapter, gate_confidence, and default_hidden
from glTF node extras". So a component gate marked `default_hidden` or
`chapter_to_verify` is only enforceable if some node in the GLB carries that
component_id in its extras. Two models declare gates they cannot honour:

  arabasta-kingdom :: yuba-oasis        default_hidden, and 9 nodes named
                                        "yuba district", "yuba 1 house", ... are
                                        in the file with NO component_id on them.
  water-7-sea-train-network :: day-station, rocketman, aqua-laguna
                                        default_hidden; "Day Station" and the
                                        Shift Station nodes are present, and the
                                        GLB's only extras are `coordinate_status`
                                        and `preview_vehicle` — not one
                                        component_id in the whole file.

Rendering either would draw geometry the manifest itself says to hide. Contrast
skypiea-sky-system, which declares giant-jack and golden-belfry-cloud withheld
and simply DOES NOT SHIP THAT GEOMETRY — withheld at export, nothing to leak,
correct. That is the difference this check measures: not "does the model declare
a gate" but "could the app actually honour it".

Both of the asset track's verifiers pass all 16 models, so this is not a
disagreement with them — they check that the models are well-formed, which they
are. Nobody was checking whether a declared gate had anything to bite on.

Inputs   blender-assets/manifests/runtime-3d.json
         blender-assets/queue/asset-requests.json
Output   public/art/runtime/<id>.glb + public/art/runtime/<id>.png
         (+ data/generated/runtime_assets.json)

Run: python3 scripts/sync_runtime_assets.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "blender-assets"
OUT_DIR = ROOT / "public" / "art" / "runtime"
OUT_JSON = ROOT / "data" / "generated" / "runtime_assets.json"


class DataError(Exception):
    pass


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def gltf_json(p: Path) -> dict:
    """The JSON chunk of a .glb. We only ever READ these bytes."""
    b = p.read_bytes()
    if b[:4] != b"glTF":
        raise DataError(f"{p.name} is not a glb")
    clen, _ = struct.unpack("<II", b[12:20])
    return json.loads(b[20 : 20 + clen])


def tagged_component_ids(j: dict) -> dict[str, int]:
    """component_id -> node count, read from glTF node extras."""
    out: dict[str, int] = {}
    for n in j.get("nodes", []):
        cid = (n.get("extras") or {}).get("component_id")
        if cid:
            out[cid] = out.get(cid, 0) + 1
    return out


def ungateable(m: dict, j: dict) -> list[str]:
    """Withheld component gates with no node in the GLB to hide. See the header."""
    tagged = tagged_component_ids(j)
    bad = []
    for g in (m.get("integration") or {}).get("component_gates") or []:
        withheld = g.get("default_hidden") or g.get("verification") == "chapter_to_verify"
        if not withheld:
            continue
        if g["id"] in tagged:
            continue
        # No tagged node. Harmless IF the geometry is absent (withheld at export,
        # like skypiea's giant-jack); a leak if it is present but untagged. We
        # cannot prove absence from a name, so the check is conservative in the
        # only direction that is safe: refuse, and say which gate.
        why = "default_hidden" if g.get("default_hidden") else str(g.get("verification"))
        bad.append(f"{g['id']} ({why})")
    return bad


def main() -> int:
    manifest = json.loads((ASSETS / "manifests" / "runtime-3d.json").read_text())
    queue = {a["id"]: a for a in json.loads((ASSETS / "queue" / "asset-requests.json").read_text())["assets"]}

    schema = manifest.get("schema_version")
    if schema != 2:
        raise DataError(f"runtime-3d.json is schema_version {schema!r}; this script reads 2")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copied, refused = [], []

    for m in manifest["models"]:
        mid = m["id"]
        q = queue.get(mid)
        state = q["state"] if q else None
        if state != "integration_ready":
            refused.append({"id": mid, "why": f"queue state is {state!r}, not integration_ready"})
            continue

        glb = ASSETS / m["glb"]
        want = (m.get("build") or {}).get("glb_sha256")
        if not glb.exists():
            refused.append({"id": mid, "why": f"glb missing: {m['glb']}"})
            continue
        if not want:
            refused.append({"id": mid, "why": "no build.glb_sha256 — refusing to ship unsigned bytes"})
            continue
        if sha256(glb) != want:
            refused.append({"id": mid, "why": "glb bytes do not match the manifest's sha256"})
            continue

        j = gltf_json(glb)
        bad = ungateable(m, j)
        if bad:
            refused.append({
                "id": mid,
                "why": "declares withheld component(s) with no tagged node to hide: " + ", ".join(bad),
                "actionable": "tag the geometry with component_id in the glTF node extras, or omit it from the export",
            })
            continue

        # The fallback. v2 moved it under `fallback` with its own sha256; the two
        # pilots still carry the v1 `fallback_raster` string beside it.
        fb = m.get("fallback") or {}
        fb_path = fb.get("path") or m.get("fallback_raster")
        if not fb_path:
            refused.append({"id": mid, "why": "no fallback declared"})
            continue
        src = ASSETS / fb_path
        if not src.exists():
            refused.append({"id": mid, "why": f"fallback missing: {fb_path}"})
            continue
        if fb.get("sha256") and sha256(src) != fb["sha256"]:
            refused.append({"id": mid, "why": "fallback bytes do not match the manifest's sha256"})
            continue

        png_dst = OUT_DIR / f"{mid}.png"
        glb_dst = OUT_DIR / f"{mid}.glb"
        shutil.copyfile(src, png_dst)
        shutil.copyfile(glb, glb_dst)

        integ = m.get("integration") or {}
        pol = m.get("runtime_policy") or {}
        beats = integ.get("chapter_beats") or {}
        # A beat set the asset track itself flags as unverified is NOT a gate.
        # Wano says: "proposed; exact waterfall climb beats need human
        # verification". The registry calls that gate_unverified and withholds it;
        # the asset being ready is a different question from the chapter being known.
        unverified = bool(beats.get("status")) or any(
            v is None for k, v in beats.items() if k != "status" and not isinstance(v, dict)
        )
        copied.append({
            "id": mid,
            "label": m.get("label"),
            "glb": f"/art/runtime/{mid}.glb",
            "glb_bytes": glb_dst.stat().st_size,
            "glb_sha256": want,
            "raster": f"/art/runtime/{mid}.png",
            "bytes": png_dst.stat().st_size,
            "maturity": m.get("maturity"),
            # The anchors and the model's own bounds are what let the app derive a
            # metres-per-unit instead of inventing one. Carried through so that
            # derivation reads declared data at runtime rather than a number
            # somebody typed into a .ts file. bounds_blender is Z-up; the exported
            # glTF is Y-up. Same span either way.
            "anchor": integ.get("anchor") or integ.get("source_anchor"),
            "source_anchor": integ.get("source_anchor"),
            "destination_anchor": integ.get("destination_anchor"),
            "anchor_confidence": integ.get("anchor_confidence"),
            "bounds_blender": (m.get("stats") or {}).get("bounds_blender"),
            "mode": integ.get("mode"),
            "fallback_mode": integ.get("fallback_mode"),
            "coordinates": integ.get("coordinates"),
            "runtime_module": integ.get("runtime_module"),
            "chapter_beats": beats,
            "component_gates": integ.get("component_gates") or [],
            "tagged_component_ids": tagged_component_ids(j),
            "layout_status": integ.get("layout_status"),
            "projection_support": integ.get("projection_support"),
            "gate_unverified": unverified,
            "feature_flag": pol.get("feature_flag") or manifest.get("feature_flag"),
            "runtime_policy": pol,
            "source_ref": f"blender-assets/{fb_path}",
            "glb_source_ref": f"blender-assets/{m['glb']}",
        })

    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/sync_runtime_assets.py",
            "schema_version": schema,
            "feature_flag": manifest.get("feature_flag"),
            "note": (
                "Only integration_ready entries whose bytes match their sha256 AND whose "
                "withheld component gates each resolve to a tagged glTF node are copied. "
                "A model that declares default_hidden geometry it cannot address is refused: "
                "the app would otherwise draw what the manifest says to hide."
            ),
            "counts": {"copied": len(copied), "refused": len(refused)},
        },
        "assets": copied,
        "refused": refused,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    for c in copied:
        gate = "  gate_unverified" if c["gate_unverified"] else ""
        print(f"  copied  {c['id']:32} glb {c['glb_bytes']:>9,}  png {c['bytes']:>9,}{gate}")
    for r in refused:
        print(f"  REFUSED {r['id']:32} {r['why']}")
    print(f"\n{len(copied)} copied, {len(refused)} refused -> {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as e:
        print(f"\nsync_runtime_assets: {e}\n", file=sys.stderr)
        sys.exit(1)
