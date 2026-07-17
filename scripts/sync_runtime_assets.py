#!/usr/bin/env python3
"""sync_runtime_assets.py — copy the SANCTIONED runtime assets into public/.
MACHINE-OWNED.

THE MANIFEST IS THE BOUNDARY, NOT CHAT HISTORY. The asset track's WORKFLOW says
it in those words: "Claude Code reads the manifests and integrates only approved
assets behind chapter gates and a feature flag." So this script reads
manifests/runtime-3d.json, checks the asset's own queue state, and copies
nothing else. A human deciding an asset "looks done" is not an input here.

WHAT IT REFUSES:
  - anything whose queue state is not `integration_ready`. Today that is every
    one of the 11 v2 narrative scenes (they are at visual_contract /
    system_sketch / scene_3d), and both of their blockouts are additionally
    marked runtime_export:false, hard-asserted by the asset track's own
    verifier. A `scene_3d` entry is reviewable source, not permission.
  - anything whose bytes do not match the sha256 the manifest recorded.

WHAT IT COPIES: the fallback raster AND the .glb of the two entries that ARE
integration_ready and addressed to us (`next: claude_code_pilot`) — the Skypiea
Knock-Up Stream and the Wano waterfall ascent.

The GLB is new here, and the reason it was refused has expired rather than been
overruled. This script used to say: "NOT the .glb — the GLB upgrade needs a 3D
renderer MapLibre does not have (a CustomLayerInterface plus three.js, ~600KB).
The Skypiea ascent was built deliberately without three.js; adding it should be a
decision someone makes on purpose, not a side effect of a sync script." That was
true and it held the line for exactly as long as it should have. The decision has
now been made on purpose: components/glb-layer.ts is that renderer. So the
condition is met and the refusal lifts. `runtime_policy.default` is still
"fallback_raster" and both files still ship — the raster is what a far-zoom or
globe-projection reader sees, per `enable_glb_when`, so it is the default in
fact and not only in the manifest.

Inputs   blender-assets/manifests/runtime-3d.json
         blender-assets/queue/asset-requests.json
Output   public/art/runtime/<id>.png + public/art/runtime/<id>.glb
         (+ data/generated/runtime_assets.json)

Run: python3 scripts/sync_runtime_assets.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
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


def main() -> int:
    manifest = json.loads((ASSETS / "manifests" / "runtime-3d.json").read_text())
    queue = {a["id"]: a for a in json.loads((ASSETS / "queue" / "asset-requests.json").read_text())["assets"]}

    flag = manifest.get("feature_flag")
    if not flag:
        raise DataError("runtime-3d.json declares no feature_flag — refusing to invent one")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copied, refused = [], []

    for m in manifest["models"]:
        mid = m["id"]
        q = queue.get(mid)
        state = q["state"] if q else None
        if state != "integration_ready":
            refused.append({"id": mid, "why": f"queue state is {state!r}, not integration_ready"})
            continue

        # The GLB's integrity. This was always checked, back when the bytes were
        # only inspected and not shipped — the reasoning being that if they moved
        # under the manifest the whole entry was suspect and the raster beside it
        # was no more trustworthy than the model. Now that we serve these bytes to
        # a browser it stops being a smell test and becomes the actual gate: the
        # sha256 in `build` is the asset track's signature on this exact file.
        glb = ASSETS / m["glb"]
        want = (m.get("build") or {}).get("glb_sha256")
        if not glb.exists():
            refused.append({"id": mid, "why": f"glb missing: {m['glb']}"})
            continue
        if not want:
            refused.append({"id": mid, "why": "manifest declares no build.glb_sha256 — refusing to ship unsigned bytes"})
            continue
        if sha256(glb) != want:
            refused.append({"id": mid, "why": "glb bytes do not match the manifest's sha256"})
            continue

        src = ASSETS / m["fallback_raster"]
        if not src.exists():
            refused.append({"id": mid, "why": f"fallback raster missing: {m['fallback_raster']}"})
            continue

        dst = OUT_DIR / f"{mid}.png"
        shutil.copyfile(src, dst)
        glb_dst = OUT_DIR / f"{mid}.glb"
        shutil.copyfile(glb, glb_dst)
        beats = (m.get("integration") or {}).get("chapter_beats") or {}
        # A beat set the asset track itself flags as unverified is NOT a gate.
        # Wano says: "proposed; exact waterfall climb beats need human
        # verification". The registry calls that gate_unverified and withholds it;
        # the asset being ready is a different question from the chapter being known.
        unverified = bool(beats.get("status")) or any(
            v is None for k, v in beats.items() if k != "status"
        )
        integ = m.get("integration") or {}
        copied.append({
            "id": mid,
            "raster": f"/art/runtime/{mid}.png",
            "bytes": dst.stat().st_size,
            "glb": f"/art/runtime/{mid}.glb",
            "glb_bytes": glb_dst.stat().st_size,
            "glb_sha256": want,
            # The two anchors and the model's own bounds are what let the app
            # derive a metres-per-unit instead of inventing one: the model's
            # vertical span IS the distance between the anchors. Carried through
            # so that derivation reads declared data at runtime rather than a
            # number somebody once typed into a .ts file. bounds_blender is Z-up
            # (Blender); the exported glTF is Y-up. Same span either way.
            "source_anchor": integ.get("source_anchor"),
            "destination_anchor": integ.get("destination_anchor"),
            "bounds_blender": (m.get("stats") or {}).get("bounds_blender"),
            "mode": integ.get("mode"),
            "coordinates": integ.get("coordinates"),
            "runtime_module": integ.get("runtime_module"),
            "chapter_beats": beats,
            "gate_unverified": unverified,
            "runtime_policy": m.get("runtime_policy"),
            "source_ref": f"blender-assets/{m['fallback_raster']}",
            "glb_source_ref": f"blender-assets/{m['glb']}",
        })

    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/sync_runtime_assets.py",
            "feature_flag": flag,
            "note": (
                "Only queue entries marked integration_ready are copied, and only when the "
                "bytes match the manifest's build.glb_sha256. Both the raster and the GLB "
                "ship: runtime_policy.default is fallback_raster, which is a real default "
                "and not a formality — enable_glb_when requires close zoom and a supported "
                "projection, so the raster is what a far-zoom reader actually sees."
            ),
            "counts": {"copied": len(copied), "refused": len(refused)},
        },
        "assets": copied,
        "refused": refused,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    print(f"feature flag: {flag}")
    for c in copied:
        gate = " (gate_unverified — the app will withhold it)" if c["gate_unverified"] else ""
        print(f"  copied  {c['id']:28} raster {c['bytes']:>9,}  glb {c['glb_bytes']:>9,}  mode={c['mode']}{gate}")
    for r in refused:
        print(f"  refused {r['id']:28} {r['why']}")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as e:
        print(f"\nsync_runtime_assets: {e}\n", file=sys.stderr)
        sys.exit(1)
