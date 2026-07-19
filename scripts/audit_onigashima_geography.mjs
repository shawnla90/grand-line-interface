#!/usr/bin/env node
/** Deterministic proof that Onigashima is actual moving GLB geography. */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { makeNodeVisible, sampleRuntimeAnimation } from "../components/runtime-models.ts";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const registry = JSON.parse(fs.readFileSync(path.join(root, "data/generated/runtime_assets.json"), "utf8"));
const asset = registry.assets.find((item) => item.id === "wano-onigashima-country-system");
assert(asset, "Wano/Onigashima is missing from the generated runtime registry");
assert.equal(registry._meta.counts.copied, 22);
assert.equal(registry._meta.counts.refused, 0);
assert.equal(asset.animation_plan.geographic_tracks.length, 1);

const track = asset.animation_plan.geographic_tracks[0];
assert.equal(track.name, "onigashima_geographic_shift");
assert.deepEqual(track.keyframes.map((item) => item.chapter), [793, 996, 997, 1027, 1039, 1049, 1108, 1109]);

function progress(chapter) {
  const sample = sampleRuntimeAnimation(asset.animation_plan, chapter, 0, false);
  assert(sample, `missing geographic sample at chapter ${chapter}`);
  const clip = sample.clips.find((item) => item.name === "onigashima_geographic_shift");
  assert(clip, `missing geographic clip at chapter ${chapter}`);
  assert.equal(sample.animate, false, "chapter geography must not create an autonomous repaint loop");
  return clip.progress;
}

assert.equal(progress(793), 0);
assert.equal(progress(996), 0);
assert(Math.abs(progress(997) - 0.17266187) < 1e-8);
assert(progress(1012) > progress(997) && progress(1012) < progress(1027));
assert(Math.abs(progress(1039) - 0.64028777) < 1e-8);
assert(Math.abs(progress(1049) - 0.78417266) < 1e-8);
assert.equal(progress(1188), 1);
assert.equal(progress(900), 0, "scrubbing backward must restore offshore geography");

let chapter = 996;
const visible = makeNodeVisible(asset, () => chapter);
const flameCloud = {
  component_id: "onigashima-flame-clouds",
  reveal_chapter: 997,
  gate_confidence: "verified_state_window",
  default_hidden: true,
  active_through_chapter: 1048.999,
};
assert.equal(visible(flameCloud, "flame cloud"), false);
chapter = 997;
assert.equal(visible(flameCloud, "flame cloud"), true);
chapter = 1048;
assert.equal(visible(flameCloud, "flame cloud"), true);
chapter = 1049;
assert.equal(visible(flameCloud, "flame cloud"), false);

function glbJson(file) {
  const bytes = fs.readFileSync(file);
  const jsonLength = bytes.readUInt32LE(12);
  const jsonType = bytes.readUInt32LE(16);
  assert.equal(jsonType, 0x4e4f534a);
  return JSON.parse(bytes.subarray(20, 20 + jsonLength).toString("utf8").trim());
}

const glb = glbJson(path.join(root, "public/art/runtime/wano-onigashima-country-system.glb"));
assert(glb.animations.some((item) => item.name === "onigashima_geographic_shift"));
const geographicRoot = glb.nodes.find((item) => item.name === "Onigashima geographic root");
assert(geographicRoot && geographicRoot.children.length >= 35,
       "skull, fortress, port, roads, katana, and clouds must share one moving hierarchy");
const flames = glb.nodes.filter((item) => item.extras?.component_id === "onigashima-flame-clouds");
assert.equal(flames.length, 14);

console.log("Onigashima geographic shift: PASS");
console.log("  actual GLB root hierarchy moves across chapter checkpoints");
console.log("  chapter interpolation reverses deterministically");
console.log("  flame clouds: visible ch997-1048 only");
console.log("  settlement/return states: ch1049 and ch1109");
