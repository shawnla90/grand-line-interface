#!/usr/bin/env python3
"""shoot_models.py — photograph every Blender model and build a contact sheet.

THE POINT IS JUDGEMENT, NOT PASS/FAIL. audit_glb already proves the gates hold;
nothing here asserts. This exists because eleven models were placed and scaled
overnight by rules nobody has looked at yet, and "the scale is a visual fit" is a
claim about how something LOOKS. Only eyes settle that. So: one page, every model
at its own gate chapter, both projections, and the reasons the three refused ones
are not there.

It also breaks a bootstrap. config/projection-overrides.ts says a model earns its
place in GLOBE_PROVEN by being photographed rendering on the globe — but a model
outside that list will not render on the globe, so it can never be photographed.
This script forces the override (GLI_FORCE_GLOBE=1), shoots everything, and prints
the list of ids that actually put pixels on a globe frame. That list is what goes
in the file: evidence first, entry second.

Run: python3 scripts/shoot_models.py --base http://localhost:3311
Needs a DEV server with NEXT_PUBLIC_RUNTIME_3D_ASSETS=1 (window.__map is dev-only).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "review" / "glb"
ART = ROOT / "data" / "generated" / "runtime_assets.json"


def build_table() -> list[dict]:
    """Mirror components/runtime-models.ts, so the sheet reports what the app does."""
    d = json.loads(ART.read_text())
    rows = []
    for a in d["assets"]:
        b = a.get("chapter_beats") or {}
        gates = a.get("component_gates") or []
        per = any(
            g.get("default_hidden") is True
            or g.get("verification") == "chapter_to_verify"
            or g.get("reveal_chapter") is None
            or (isinstance(g.get("reveal_chapter"), int) and g["reveal_chapter"] != b.get("base_reveal"))
            for g in gates
        )
        ch = b.get("base_reveal") if per and b.get("base_reveal") else (b.get("safe_full_scene") or b.get("base_reveal"))
        skipped = None
        if a.get("gate_unverified"):
            skipped = "gate_unverified — its own manifest calls the beats proposed"
        elif not a.get("anchor"):
            skipped = "no anchor"
        elif ch is None:
            skipped = "no base_reveal or safe_full_scene"
        mode = (
            "measured (1 unit = 1 degree, vs the shipped coastline)" if a["id"] == "fish-man-island"
            else "derived from its two anchors" if "knock-up" in a["id"]
            else "visual_fit — scaled to the island's own silhouette"
        )
        rows.append({
            "id": a["id"], "label": a.get("label") or a["id"], "anchor": a.get("anchor"),
            "reveal": ch, "perNode": per, "scale": mode, "skipped": skipped,
            "withheld": a.get("withheld_variants") or [],
            "contradictions": a.get("gate_contradictions") or [],
            "projection_support": a.get("projection_support"),
            "layout_status": a.get("layout_status"),
            "route_policy": a.get("route_policy"),
            "glb_bytes": a.get("glb_bytes"),
        })
    return rows, d.get("refused", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3311")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    table, refused = build_table()

    globe_proven: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1000, "height": 700})
        for row in table:
            if row["skipped"] or row["reveal"] is None:
                print(f"  skip  {row['id']:32} {row['skipped']}")
                continue
            for proj in ("mercator", "globe"):
                shot = OUT / f"{row['id']}--{proj}.png"
                page.goto(f"{args.base}/?ch={row['reveal']}", wait_until="networkidle")
                page.wait_for_timeout(1200)
                try:
                    page.evaluate(
                        """([lng, lat, proj]) => {
                            const m = window.__map;
                            m.setProjection({ type: proj });
                            m.jumpTo({ center: [lng, lat], zoom: 6.0, pitch: 55 });
                        }""",
                        [row["anchor"][0], row["anchor"][1], proj],
                    )
                except Exception as e:
                    print(f"  FAIL  {row['id']} {proj}: {e}")
                    continue
                page.wait_for_timeout(5200)
                present = page.evaluate(f"() => !!window.__map.getLayer('glb-{row['id']}')")
                if present:
                    before = page.locator("canvas").first.screenshot()
                    page.locator("canvas").first.screenshot(path=str(shot))
                    page.evaluate(f"() => window.__map.removeLayer('glb-{row['id']}')")
                    page.wait_for_timeout(900)
                    drew = before != page.locator("canvas").first.screenshot()
                    if proj == "globe" and drew:
                        globe_proven.append(row["id"])
                else:
                    page.locator("canvas").first.screenshot(path=str(shot))
                    drew = False
                row[f"{proj}_drew"] = drew
                row[f"{proj}_layer"] = present
                print(f"  shot  {row['id']:32} {proj:9} layer={present} pixels={drew}")
        browser.close()

    (OUT / "index.html").write_text(render(table, refused, globe_proven), encoding="utf-8")
    print(f"\nGLOBE_PROVEN (models that actually drew on a globe frame):")
    for g in sorted(set(globe_proven)):
        print(f'  "{g}",')
    print(f"\n-> {(OUT / 'index.html').relative_to(ROOT)}")
    return 0


def render(table: list[dict], refused: list[dict], globe_proven: list[str]) -> str:
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    cards = []
    for r in table:
        if r["skipped"]:
            continue
        badges = []
        if r["perNode"]:
            badges.append('<span class="b warn">per-node gated</span>')
        if r["withheld"]:
            badges.append(f'<span class="b warn">{len(r["withheld"])} withheld</span>')
        if r["contradictions"]:
            badges.append(f'<span class="b bad">{len(r["contradictions"])} gate contradiction(s)</span>')
        if r["route_policy"]:
            badges.append('<span class="b">derived_schematic</span>')
        shots = "".join(
            f'<figure><img src="{r["id"]}--{p}.png" loading="lazy"><figcaption>{p}'
            f'{" — did not draw" if not r.get(f"{p}_drew") else ""}</figcaption></figure>'
            for p in ("mercator", "globe")
        )
        cards.append(f"""<article>
  <h2>{esc(r["label"])}</h2>
  <p class="meta">gate ch.{r["reveal"]} · {esc(r["scale"])} · {(r["glb_bytes"] or 0)//1024} KB</p>
  <p class="badges">{"".join(badges)}</p>
  <div class="shots">{shots}</div>
  <details><summary>detail</summary><pre>{esc(json.dumps({k: r[k] for k in ("id","anchor","layout_status","projection_support","withheld","contradictions")}, indent=1))}</pre></details>
</article>""")
    ref = "".join(
        f'<li><b>{esc(x["id"])}</b> — {esc(x["why"])}<br><i>{esc(x.get("actionable",""))}</i></li>'
        for x in refused
    )
    skipped = "".join(
        f'<li><b>{esc(r["id"])}</b> — {esc(r["skipped"])}</li>' for r in table if r["skipped"]
    )
    return f"""<!doctype html><meta charset="utf-8"><title>Blender models — contact sheet</title>
<style>
:root{{color-scheme:dark}}
body{{background:#080b11;color:#e8eef7;font:14px/1.5 ui-sans-serif,system-ui;margin:0;padding:32px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#8fa3bd;margin:0 0 28px}}
article{{border:1px solid #1e2b3d;border-radius:10px;padding:16px;margin-bottom:20px;background:#0c111a}}
h2{{font-size:16px;margin:0 0 2px}} .meta{{color:#8fa3bd;margin:0 0 8px;font-size:12px}}
.shots{{display:flex;gap:12px;flex-wrap:wrap}} figure{{margin:0;flex:1 1 380px;min-width:0}}
img{{width:100%;border-radius:6px;border:1px solid #1e2b3d;display:block}}
figcaption{{color:#7e93ad;font-size:11px;padding-top:4px}}
.b{{display:inline-block;background:#16233a;color:#9dc0ee;border-radius:4px;padding:1px 7px;font-size:11px;margin-right:5px}}
.b.warn{{background:#3a2f16;color:#e8c877}} .b.bad{{background:#3d1c1c;color:#f0a0a0}}
pre{{background:#070a10;padding:10px;border-radius:6px;overflow:auto;font-size:11px;color:#9fb4cd}}
ul{{color:#c9d6e6}} li{{margin-bottom:8px}} i{{color:#8fa3bd}}
section{{border:1px solid #1e2b3d;border-radius:10px;padding:16px;margin-bottom:20px;background:#0c111a}}
</style>
<h1>Blender models on the map</h1>
<p class="sub">Every model at its own gate chapter, zoom 6, pitch 55, both projections. These are
<code>runtime_blockout_v1</code> — deliberately not final art. The question is placement, scale and gate, not beauty.</p>
<section><h2>Refused by the sync ({len(refused)})</h2><ul>{ref}</ul></section>
{f'<section><h2>Skipped by the table</h2><ul>{skipped}</ul></section>' if skipped else ''}
{"".join(cards)}
<section><h2>Drew on a globe frame ({len(set(globe_proven))})</h2>
<p class="sub">These are the ids that earn a place in <code>config/projection-overrides.ts</code>.</p>
<pre>{esc(chr(10).join(sorted(set(globe_proven))))}</pre></section>
"""


if __name__ == "__main__":
    sys.exit(main())
