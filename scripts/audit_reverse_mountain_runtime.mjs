#!/usr/bin/env node
/** Deterministic chapter, label, animation, and node-gate proof for W1. */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  makeNodeVisible,
  modelAnchorDistanceDeg,
  runtimeLabelAt,
  sampleRuntimeAnimation,
} from "../components/runtime-models.ts";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const registry = JSON.parse(fs.readFileSync(path.join(root, "data/generated/runtime_assets.json"), "utf8"));
const asset = registry.assets.find((item) => item.id === "reverse-mountain-twin-cape-voyage");
assert(asset, "Reverse Mountain is missing from the generated runtime registry");
assert.equal(registry._meta.counts.copied, 17);
assert.equal(registry._meta.counts.refused, 0);
assert.equal(modelAnchorDistanceDeg([-179, -2], [179, -2]), 2);
assert(modelAnchorDistanceDeg([-179, -2], [-120, 0]) > 13);
assert.equal(asset.fx_masks.length, 5);
for (const mask of asset.fx_masks) {
  assert(fs.existsSync(path.join(root, "public", mask.url)), `served mask missing: ${mask.url}`);
}

assert.equal(runtimeLabelAt(asset, "laboon", 102), "Unidentified giant whale");
assert.equal(runtimeLabelAt(asset, "laboon", 103), "Laboon");
assert.equal(runtimeLabelAt(asset, "laboon", 101), null);

const plan = asset.animation_plan;
assert(plan, "animation plan missing");
assert.equal(sampleRuntimeAnimation(plan, 100, 0, false), null);
const ascent = sampleRuntimeAnimation(plan, 101, 0, false);
assert.deepEqual(ascent.clips.map((item) => item.name).sort(), ["current_ascent_flow_loop", "merry_ascent_climb"]);
assert.equal(ascent.animate, true);
const crest = sampleRuntimeAnimation(plan, 101, 5000, false);
assert(crest.clips.some((item) => item.name === "merry_summit_crest"));
assert(!crest.clips.some((item) => item.name === "merry_ascent_climb"));
const contact = sampleRuntimeAnimation(plan, 102, 4000, false);
assert(contact.clips.some((item) => item.name === "laboon_mouth_open_swallow"));
assert(contact.clips.some((item) => item.name === "merry_swallowed_transition"));
const reduced = sampleRuntimeAnimation(plan, 105, 0, true);
assert.equal(reduced.animate, false);
assert(reduced.clips.some((item) => item.name === "merry_twin_cape_departure" && item.progress === 1));
assert.deepEqual(
  sampleRuntimeAnimation(plan, 104, 2345, false),
  sampleRuntimeAnimation(plan, 104, 2345, false),
  "identical animation inputs must produce identical samples",
);

let chapter = 100;
const visible = makeNodeVisible(asset, () => chapter);
const node = (component_id, extras = {}) => ({ component_id, ...extras });
assert.equal(visible(node("reverse-mountain-massif", { reveal_chapter: 101, default_hidden: false }), "massif"), false);
chapter = 101;
assert.equal(visible(node("reverse-mountain-massif", { reveal_chapter: 101, default_hidden: false }), "massif"), true);
assert.equal(visible(node("twin-cape", { reveal_chapter: 102, default_hidden: false }), "cape"), false);
chapter = 102;
assert.equal(visible(node("laboon-unidentified", { reveal_chapter: 102, default_hidden: false }), "whale"), true);
assert.equal(visible(node("crocus", { reveal_chapter: 103, default_hidden: false }), "crocus"), false);
chapter = 103;
assert.equal(visible(node("crocus", { reveal_chapter: 103, default_hidden: false }), "crocus"), true);
assert.equal(visible(node("laboon-interior-theatre", {
  reveal_chapter: 103,
  default_hidden: true,
  gate_confidence: "verified_state_window",
  active_through_chapter: 103.999,
}), "interior"), true);
chapter = 104;
assert.equal(visible(node("laboon-interior-theatre", {
  reveal_chapter: 103,
  default_hidden: true,
  gate_confidence: "verified_state_window",
  active_through_chapter: 103.999,
}), "interior"), false);
assert.equal(visible(node("local-whirlpool-emitter", {
  default_hidden: true,
  gate_confidence: "chapter_to_verify",
}), "whirlpool"), false);

console.log("Reverse Mountain runtime: PASS");
console.log("  spoiler-safe labels: ch102 unidentified / ch103 Laboon");
console.log("  deterministic animation states: chapters 101-105");
console.log("  node gates: pre-reveal, interior window, and whirlpool dark");
console.log("  served FX masks: 5");
