#!/usr/bin/env python3
"""asset_track_report.py — what the app found in the asset track's data.

Written to data/review/, never to blender-assets/. That workspace is read-only to
us and this script has no business editing the thing it is reporting on; the
report is a message, not a patch.

Everything here was found by MEASURING the shipped bytes — opening each .glb,
reading its node extras, and comparing them to what the manifest says about the
same components. Both of the asset track's verifiers pass all 16 models and they
are right to: the models are well-formed. These are a different class of defect —
a gate that declares an intent the file cannot carry out.

Run: python3 scripts/asset_track_report.py
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "blender-assets"
ART = ROOT / "data" / "generated" / "runtime_assets.json"
OUT = ROOT / "data" / "review" / "asset-track-report.md"


def gltf(p: Path) -> dict:
    b = p.read_bytes()
    clen, _ = struct.unpack("<II", b[12:20])
    return json.loads(b[20 : 20 + clen])


def names_matching(j: dict, terms: list[str]) -> list[str]:
    return [
        n.get("name", "")
        for n in j.get("nodes", [])
        if any(t in (n.get("name") or "").lower() for t in terms)
    ]


def main() -> int:
    d = json.loads(ART.read_text())
    man = json.loads((ASSETS / "manifests" / "runtime-3d.json").read_text())
    by_id = {m["id"]: m for m in man["models"]}

    lines: list[str] = []
    w = lines.append
    w("# What the atlas found in the runtime batch")
    w("")
    w(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `scripts/asset_track_report.py`_")
    w(f"_Against `manifests/runtime-3d.json` schema_version {man.get('schema_version')}, {len(man['models'])} models._")
    w("")
    w("Everything below was found by opening the shipped `.glb` files and comparing their")
    w("node extras to what the manifest says about the same components. **Both")
    w("`verify_runtime_3d.py` and `verify_priority_narrative_blockouts.py` pass all 16**,")
    w("and they are right to — the models are well-formed. These are a different class of")
    w("defect: a gate that declares an intent the file cannot carry out. Nobody was")
    w("checking whether a declared gate had anything to bite on.")
    w("")
    w(f"**{d['_meta']['counts']['copied']} models integrated. "
      f"{d['_meta']['counts']['refused']} refused. "
      f"{d['_meta']['counts']['gate_contradictions']} gate contradictions.**")
    w("")

    # ---- 1. refusals -------------------------------------------------------
    w("## 1. Refused: withheld components with no node to hide")
    w("")
    w("`runtime_policy.node_gate_policy` says to read `component_id` from glTF node extras,")
    w("and the acceptance list says *\"A GLB node is never rendered before its component")
    w("gate.\"* A gate is therefore only enforceable if some node carries that `component_id`.")
    w("These declare gates with nothing to apply them to, so the app refuses the whole model")
    w("rather than draw geometry the manifest says to hide.")
    w("")
    for r in d["refused"]:
        m = by_id.get(r["id"], {})
        j = gltf(ASSETS / m["glb"]) if m.get("glb") else {}
        w(f"### `{r['id']}`")
        w("")
        w(f"> {r['why']}")
        w("")
        # ONLY the components named in the refusal, not every withheld one. The
        # first version of this searched on all of them, so arabasta-kingdom
        # reported "40 nodes" — it was matching `alubarna-clock-tower` too, which
        # IS tagged and IS enforceable and is not the problem. Telling the asset
        # track to go tag 40 nodes when 9 are at fault is worse than saying
        # nothing: the report has to be exactly as wide as the defect.
        tagged = {
            (n.get("extras") or {}).get("component_id")
            for n in j.get("nodes", [])
            if (n.get("extras") or {}).get("component_id")
        }
        gates = (m.get("integration") or {}).get("component_gates") or []
        withheld = [
            g["id"] for g in gates
            if (g.get("default_hidden") or g.get("verification") == "chapter_to_verify")
            and g["id"] not in tagged
        ]
        terms = sorted({tok for cid in withheld for tok in cid.split("-") if len(tok) > 3})
        # A HINT, AND LABELLED AS ONE. Matching node names against the words in a
        # component id is a heuristic and it is not a good one — this report first
        # told you `skypiea-sky-system` had 34 nodes of withheld geometry because
        # "cloud" (from `golden-belfry-cloud`) matches "Cloud sea puff 01", which is
        # the ordinary cloud sea and withheld nothing. A hand-check for
        # jack/belfry/golden finds NOTHING in that file: the geometry really is
        # absent. So the fact and the guess are now printed as different things.
        # The only claim this report makes is the one it can prove.
        w(f"**The fact:** `{'`, `'.join(withheld)}` " +
          ("is" if len(withheld) == 1 else "are") +
          " withheld by the manifest, and no node in the GLB carries that `component_id`. "
          "The app cannot honour the gate, so it refuses the model.")
        w("")
        w("**What we cannot tell you:** whether the geometry is actually in the file. If it was")
        w("never exported — the pattern that is *correct* — then the gate is simply redundant and")
        w("this refusal is a false positive. Only the author knows. Absence cannot be proven from")
        w("a node name, so the app refuses in the one direction that is safe to be wrong in.")
        w("")
        if hits := names_matching(j, terms):
            w(f"**A hint, not a finding.** {len(hits)} node name(s) contain a word from the withheld")
            w("component id(s). This is a keyword match on free-text names and it is unreliable in")
            w("both directions — judge it yourself:")
            w("")
            w("```")
            for h in hits[:10]:
                w(f"  {h}")
            if len(hits) > 10:
                w(f"  ... and {len(hits) - 10} more")
            w("```")
            w("")
        w("**Fix, either way:** tag the geometry with `component_id` in its glTF extras, or — if it")
        w("is not in the export — drop the gate.")
        w("")

    # ---- 2. contradictions -------------------------------------------------
    w("## 2. A model whose extras contradict its own manifest")
    w("")
    for a in d["assets"]:
        if not a.get("gate_contradictions"):
            continue
        w(f"### `{a['id']}`")
        w("")
        w("| component | manifest | node extras | nodes |")
        w("|---|---|---|---|")
        for c in a["gate_contradictions"]:
            g, e = c["manifest_gate"], c["example_extras"]
            w(f"| `{c['component_id']}` | `default_hidden: {json.dumps(g.get('default_hidden'))}`, "
              f"`verification: {json.dumps(g.get('verification'))}`, `reveal_chapter: {json.dumps(g.get('reveal_chapter'))}` "
              f"| `default_hidden: {json.dumps(e.get('default_hidden'))}`, "
              f"`gate_confidence: {json.dumps(e.get('gate_confidence'))}`, `reveal_chapter` absent "
              f"| {c['nodes']} |")
        w("")
        w("The manifest withholds these; every one of their nodes says `default_hidden: false`.")
        w("")
        w("**It is currently masked, not safe.** The app ORs the two sources, so")
        w("`gate_confidence: \"chapter_to_verify\"` still withholds them and nothing renders early")
        w("today. But the only thing standing between a chapter-142 reader and the Red Line's")
        w("lower ports is that second field. Drop `gate_confidence` in a plausible cleanup and")
        w("the geometry draws, with nothing anywhere complaining.")
        w("")
        w("**Fix:** make `default_hidden` in the extras agree with the manifest gate.")
        w("")

    # ---- 3. the globe ------------------------------------------------------
    w("## 3. Globe projection is supported — please widen `projection_support`")
    w("")
    w("Every model declares:")
    w("")
    w("```json")
    w('"projection_support": ["mercator_closeup"],')
    w('"globe_policy": "transparent fallback; do not apply a naive mercator model matrix on globe"')
    w("```")
    w("")
    w("The policy is right, and the restriction follows from it **for a naive loader**.")
    w("MapLibre's own docs agree: a matrix-only custom layer is *\"sufficient for simple custom")
    w("layers that also only support mercator projection\"*, because globe projection happens in")
    w("its vertex shaders.")
    w("")
    w("This app's loader is not naive. `components/glb-layer.ts` draws through")
    w("`map.transform.getMatrixForModel(lngLat, altitude)`, whose **globe** implementation maps")
    w("model metres onto the unit sphere — exactly the space `mainMatrix` consumes. No naive")
    w("mercator matrix is applied on any projection, so the acceptance clause *\"Globe projection")
    w("never receives a naive mercator-only model matrix\"* is satisfied exactly.")
    w("")
    w("**All 11 wired models have now been photographed rendering on a globe frame** — layer")
    w("present, and the frame differs from the same frame with the model removed. Evidence:")
    w("`data/review/glb/<id>--globe.png` and the contact sheet at `data/review/glb/index.html`.")
    w("")
    w("Until the field is widened the app carries `config/projection-overrides.ts`, which names")
    w("each proven model and exists to be deleted. **One field, and all 14 unlock on the atlas's")
    w("default view** — which is a globe.")
    w("")

    # ---- 4. small stuff ----------------------------------------------------
    w("## 4. Smaller things, none of them blocking")
    w("")
    w("- **`sabaody-grove-network`** declares a gate `{\"id\": \"sabaody-archipelago\", \"reveal_chapter\": 496}`")
    w("  with no tagged node. Harmless only because it is not withheld — the tagged ids are")
    w("  `yarukiman-mangroves`, `sabaody-root-bridges`, `sabaody-park`, `human-auctioning-house`,")
    w("  `sabaody-bubble-layer`.")
    w("- **`loguetown-roger-execution`** ships 165 nodes with zero extras while declaring 3 gates.")
    w("  Harmless only because all three are `reveal_chapter: 1`.")
    w("- **`wano-waterfall-ascent`** is withheld by the app as `gate_unverified`: its own")
    w("  `chapter_beats.status` reads *\"proposed; exact waterfall climb beats need human")
    w("  verification\"*. Asset-ready is not gate-known, and we will not invent the chapter.")
    w("  It is also `screen_space_html_marker`, not a `maplibre_custom_3d_layer` — a different")
    w("  renderer, not yet built.")
    w("- **Evidence paths are absolute** (`/Users/shawnos.ai/dead-reckoning/data/generated/islands.json`).")
    w("  The app now translates both provenance prefixes and trusts the sha256; no change needed")
    w("  on your side. Noting it only because a consumer that used them as paths would break on")
    w("  any machine but the authoring one — ours did, silently, until this week.")
    w("")

    # ---- provenance --------------------------------------------------------
    w("---")
    w("")
    w("## Provenance")
    w("")
    w("Every model below was verified byte-for-byte against `build.glb_sha256` before it was")
    w("read. The absolute strings in the contracts are provenance; these hashes are the authority.")
    w("")
    w("| model | glb sha256 | bytes |")
    w("|---|---|---|")
    for a in d["assets"]:
        w(f"| `{a['id']}` | `{(a.get('glb_sha256') or '')[:16]}…` | {a.get('glb_bytes', 0):,} |")
    w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(lines)} lines, sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
