/**
 * components/wano.ts — Wano Country, the marker-style asset. PURE f(chapter).
 *
 * Wano is the one runtime model that is NOT a map-plane GLB: the asset track
 * shipped it as a vertical-transition SPRITE (a 1024×2048 portrait of the
 * waterfall climb up to the country at its crest) with
 * `mode: screen_space_html_marker` and `transform_origin: 50% 100%` — a
 * standing card whose FEET are the map anchor, exactly like the ship and the
 * Baratie marks. So it renders through the pooled HTML-marker system, not
 * glb-layer, and this module is its beat table + element factory.
 *
 * HONESTY GATE, the reason this renderer is deliberately boring: the asset's
 * own manifest says `chapter_beats: { arrival: 909, start: null, crest: null,
 * status: "proposed; exact waterfall climb beats need human verification" }`.
 * The ARRIVAL is verified; the CLIMB is not. So Wano appears at ch 909 and
 * stands — no climb animation, no invented crest chapter. When a human
 * verifies the climb beats, an altitude ramp can join skypiea.ts's pattern;
 * until then the app withholds rather than invents, same as everywhere else.
 */

/** The asset's own declared anchor (runtime_assets.json, wano-waterfall-ascent). */
export const WANO_ANCHOR: [number, number] = [118.3801, 5.3077];

/** The verified beat. The reader reaches Wano's waters at ch 909. */
export const WANO_ARRIVAL = 909;

export const WANO_SPRITE = "/art/runtime/wano-waterfall-ascent.png";

/** 0 before arrival; fades in across the arrival chapters; stands thereafter.
 * Backward scrub below 909 takes it away again — the usual contract. */
export function wanoOpacity(ch: number): number {
  if (ch < WANO_ARRIVAL) return 0;
  return Math.min(1, (ch - WANO_ARRIVAL + 1) / 3);
}

/**
 * Build (once) the DOM element MapLibre re-positions for Wano. The `wrap` is
 * returned separately for the same reason every other mark does it: MapLibre
 * owns the marker element's opacity, so scale and fades go on inner nodes.
 * Sized tall — it is a country behind a waterfall, not a pin — and scaled by
 * the shared `--gli-mark-scale` zoom variable like every pooled mark.
 */
export function makeWanoElement(): { el: HTMLDivElement; wrap: HTMLDivElement; img: HTMLImageElement } {
  const el = document.createElement("div");
  el.className = "wanoMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";

  const wrap = document.createElement("div");
  wrap.style.transform = "scale(var(--gli-mark-scale, 1))";
  wrap.style.transformOrigin = "50% 100%";

  const img = document.createElement("img");
  img.src = WANO_SPRITE;
  img.alt = "";
  img.decoding = "async";
  img.loading = "lazy";
  // Native 1024×2048; drawn at 1/16 so the country towers over the sea lane
  // without swallowing the chart. The zoom scale-wrap grows it on approach.
  img.style.width = "64px";
  img.style.height = "128px";
  img.style.filter = "drop-shadow(0 2px 6px rgba(0,0,0,0.75))";
  img.style.opacity = "0";
  img.style.transition = "opacity 400ms ease";

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "7px";
  label.style.letterSpacing = "0.14em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.color = "rgba(201,160,106,0.95)";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";
  label.textContent = "Wano";

  wrap.appendChild(img);
  wrap.appendChild(label);
  el.appendChild(wrap);
  return { el, wrap, img };
}
