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


def gate_withholds(g: dict) -> bool:
    """Does this MANIFEST component gate withhold its geometry?"""
    return bool(g.get("default_hidden")) or g.get("verification") == "chapter_to_verify" or g.get("reveal_chapter") is None


def extras_withhold(e: dict) -> bool:
    """Do these NODE extras withhold their own geometry?

    THE PREDICATE IS AN OR, AND MARY GEOISE IS WHY. Its manifest marks
    red-port-paradise, red-port-new-world and bondola-route
    `default_hidden: true, reveal_chapter: null`. Its GLB's own extras, on all 20
    of the matching nodes, say `default_hidden: false` with `reveal_chapter`
    ABSENT. The two sources contradict each other, and a gate that trusts either
    one alone draws the Red Line's lower ports for a chapter-142 reader.

    totto-land is self-consistent (32 of 99 nodes agree with their manifest), so
    nothing catches this unless the predicate is tested against Mary Geoise
    specifically. Hence: withheld if the manifest says so OR the extras say so.
    Neither source can clear geometry the other one withholds.
    """
    return (
        bool(e.get("default_hidden"))
        or e.get("gate_confidence") == "chapter_to_verify"
        or e.get("reveal_chapter") is None
    )


def contradictions(m: dict, j: dict) -> list[dict]:
    """Where the manifest's gates and the GLB's extras disagree, FIELD BY FIELD.

    It has to be field-level, and finding that out cost a wrong check first. The
    obvious version compares OUTCOMES — does the manifest withhold vs do the
    extras withhold — and on this batch it reports nothing at all. Mary Geoise
    still comes out withheld either way, because `gate_confidence:
    "chapter_to_verify"` is present on the nodes and our OR predicate catches it.

    That is a true statement about today and a useless one about tomorrow. The
    defect is real and sits one level down: the manifest says
    `default_hidden: true` and all 20 nodes say `default_hidden: false`. It is
    masked ONLY by a second field agreeing. Drop `gate_confidence` from those
    extras — a plausible cleanup on their side — and the Red Line's lower ports
    render for a chapter-142 reader with nothing anywhere complaining.

    So: compare the fields that are meant to mean the same thing, and report the
    disagreement even when it currently changes no behaviour. A check that only
    fires once the mask slips is a check that fires too late.
    """
    by_id: dict[str, list[dict]] = {}
    for n in j.get("nodes", []):
        cid = (n.get("extras") or {}).get("component_id")
        if cid:
            by_id.setdefault(cid, []).append(n["extras"])
    out = []
    for g in (m.get("integration") or {}).get("component_gates") or []:
        nodes = by_id.get(g["id"])
        if not nodes:
            continue
        m_hidden = bool(g.get("default_hidden"))
        e_hidden = any(bool(e.get("default_hidden")) for e in nodes)
        m_conf = "chapter_to_verify" if g.get("verification") == "chapter_to_verify" else "verified"
        e_conf = "chapter_to_verify" if any(e.get("gate_confidence") == "chapter_to_verify" for e in nodes) else "verified"
        bad = []
        if m_hidden != e_hidden:
            bad.append(f"default_hidden: manifest={m_hidden} extras={e_hidden}")
        if m_conf != e_conf:
            bad.append(f"confidence: manifest={m_conf} extras={e_conf}")
        if not bad:
            continue
        out.append({
            "component_id": g["id"],
            "fields": bad,
            "nodes": len(nodes),
            # Does our OR predicate still withhold it despite the disagreement?
            # Today this is True for every case, which is exactly why it needs
            # saying out loud rather than being taken as an all-clear.
            "still_withheld_by_or_predicate": gate_withholds(g) or any(extras_withhold(e) for e in nodes),
            "manifest_gate": g,
            "example_extras": nodes[0],
        })
    return out


def ungateable(m: dict, j: dict) -> list[str]:
    """Withheld component gates with no node in the GLB to hide. See the header."""
    tagged = tagged_component_ids(j)
    bad = []
    for g in (m.get("integration") or {}).get("component_gates") or []:
        if not gate_withholds(g):
            continue
        if g["id"] in tagged:
            continue
        # No tagged node. Harmless IF the geometry is absent (withheld at export,
        # like skypiea's giant-jack); a leak if it is present but untagged. We
        # cannot prove absence from a name, so the check is conservative in the
        # only direction that is safe: refuse, and say which gate.
        why = "default_hidden" if g.get("default_hidden") else str(g.get("verification") or "no reveal_chapter")
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

        integ = m.get("integration") or {}

        # Optional reusable shader/particle control masks. They are signed with
        # the model, but copied beside it rather than embedded so both the web
        # runtime and an Unreal import adapter can address the same RGBA fields.
        fx_masks = []
        mask_error = None
        for mask in integ.get("fx_masks") or []:
            rel = mask.get("path")
            want_mask = mask.get("sha256")
            mask_src = ASSETS / rel if rel else None
            if not rel or not want_mask or mask_src is None or not mask_src.exists():
                mask_error = f"FX mask is missing path/hash/bytes: {mask.get('id')!r}"
                break
            if sha256(mask_src) != want_mask:
                mask_error = f"FX mask bytes do not match sha256: {mask.get('id')!r}"
                break
            mask_dst = OUT_DIR / mid / "masks" / mask_src.name
            mask_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(mask_src, mask_dst)
            fx_masks.append({
                **mask,
                "url": f"/art/runtime/{mid}/masks/{mask_src.name}",
                "bytes": mask_dst.stat().st_size,
            })
        if mask_error:
            refused.append({"id": mid, "why": mask_error})
            continue

        png_dst = OUT_DIR / f"{mid}.png"
        glb_dst = OUT_DIR / f"{mid}.glb"
        shutil.copyfile(src, png_dst)
        shutil.copyfile(glb, glb_dst)

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
            "label_gates": integ.get("label_gates") or [],
            "animation_plan": integ.get("animation_plan") or None,
            "fx_masks": fx_masks,
            "tagged_component_ids": tagged_component_ids(j),
            "layout_status": integ.get("layout_status"),
            "projection_support": integ.get("projection_support"),
            # THE FIVE FIELDS THIS SCRIPT USED TO DROP, each load-bearing:
            #
            # scale_policy — on 13 of 16 (all but the three with bespoke
            #   derivations). `visual_fit_not_canon_scale` + `use_model_bounds` is
            #   the manifest telling us there is NO canon metres-per-unit to find
            #   and to fit the bounds instead. Dropping it invited us to go
            #   inventing one, which is the exact mistake the Knock-Up Stream's
            #   comment block spends 20 lines warning about.
            # anchor_usage / anchor_warning — "atlas_anchor_only", "never use it
            #   as evidence of relative canon topology". The anchor places; it
            #   does not measure. Skypiea's two-anchor trick exists on no other
            #   model.
            # withheld_variants — the declared list of components to hide, by id.
            #   Cleaner than reading it out of node extras, and it is the asset
            #   track's own statement of intent rather than our inference.
            # route_policy — "local relationship schematic; never project local
            #   bearings as canon globe geometry" (2 models). This IS the
            #   derived_schematic labelling the original brief demanded; it must
            #   reach the UI, not die here.
            "scale_policy": integ.get("scale_policy"),
            "anchor_usage": integ.get("anchor_usage"),
            "anchor_warning": integ.get("anchor_warning"),
            "withheld_variants": integ.get("withheld_variants") or [],
            "route_policy": integ.get("route_policy"),
            # Where the manifest and the model's own extras disagree. Never
            # absorbed silently: it is the asset track's bug and only we can see it.
            "gate_contradictions": contradictions(m, j),
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
            "counts": {
                "copied": len(copied),
                "refused": len(refused),
                "gate_contradictions": sum(len(c["gate_contradictions"]) for c in copied),
            },
        },
        "assets": copied,
        "refused": refused,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    contra = [(c["id"], x) for c in copied for x in c["gate_contradictions"]]
    for c in copied:
        gate = "  gate_unverified" if c["gate_unverified"] else ""
        n = len(c["gate_contradictions"])
        warn = f"  !! {n} gate contradiction(s)" if n else ""
        print(f"  copied  {c['id']:32} glb {c['glb_bytes']:>9,}  png {c['bytes']:>9,}{gate}{warn}")
    for r in refused:
        print(f"  REFUSED {r['id']:32} {r['why']}")
    if contra:
        print("\n  GATE CONTRADICTIONS — the manifest and the model's own extras disagree.")
        print("  Neither source can clear geometry the other withholds, so the app ORs them")
        print("  and hides. Reported upstream; it is the asset track's data to fix.")
        for mid, x in contra:
            masked = " (still withheld by the OR predicate — masked, not safe)" if x["still_withheld_by_or_predicate"] else " !! NOT WITHHELD"
            print(f"    {mid} :: {x['component_id']:22} {'; '.join(x['fields'])}  ({x['nodes']} nodes){masked}")
    print(f"\n{len(copied)} copied, {len(refused)} refused -> {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as e:
        print(f"\nsync_runtime_assets: {e}\n", file=sys.stderr)
        sys.exit(1)
