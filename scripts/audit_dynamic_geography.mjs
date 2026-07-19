#!/usr/bin/env node
/** Deterministic proof for Water 7, Red Line, and Fish-Man descent geography. */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { makeNodeVisible, sampleRuntimeAnimation } from "../components/runtime-models.ts";
import { RED_LINE_LAND } from "../components/world-geometry.ts";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const registry = JSON.parse(fs.readFileSync(path.join(root, "data/generated/runtime_assets.json"), "utf8"));
const byId = new Map(registry.assets.map((item) => [item.id, item]));
assert.equal(registry._meta.counts.copied, 22);
assert.equal(registry._meta.counts.refused, 0);

function clip(asset, chapter, name, elapsed = 0) {
  const sample = sampleRuntimeAnimation(asset.animation_plan, chapter, elapsed, false);
  assert(sample, `${asset.id} has no sample at chapter ${chapter}`);
  return sample.clips.find((item) => item.name === name);
}

const water = byId.get("water-7-sea-train-network");
assert(water?.animation_plan);
assert(clip(water, 322, "water7_puffing_tom_route_cycle", 2521));
assert.equal(clip(water, 362, "water7_aqua_laguna_tide_state")?.progress, 0);
assert.equal(clip(water, 363, "water7_aqua_laguna_tide_state")?.progress, .2);
assert.equal(clip(water, 367, "water7_aqua_laguna_tide_state")?.progress, 1);
assert.equal(clip(water, 368, "water7_aqua_laguna_tide_state"), undefined);
assert(clip(water, 375, "water7_rocketman_route_state"));
assert(clip(water, 375, "water7_enies_waterfall_cycle", 2104));

let chapter = 362;
const waterVisible = makeNodeVisible(water, () => chapter);
const aqua = {
  component_id: "aqua-laguna", reveal_chapter: 363,
  gate_confidence: "verified_state_window", default_hidden: true,
  active_through_chapter: 367.999,
};
assert.equal(waterVisible(aqua), false);
chapter = 363;
assert.equal(waterVisible(aqua), true);
chapter = 368;
assert.equal(waterVisible(aqua), false);

const mary = byId.get("mary-geoise-red-line");
assert(mary?.animation_plan);
assert(clip(mary, 142, "red_line_cloud_drift", 2521));
assert.equal(clip(mary, 904, "mary_geoise_bondola_cycle"), undefined);
assert(clip(mary, 905, "mary_geoise_bondola_cycle", 2521));
assert.match(mary.transport_policy, /people/);
assert.match(mary.transport_policy, /original ships remain/);
let maryChapter = 1188;
const maryVisible = makeNodeVisible(mary, () => maryChapter);
assert.equal(maryVisible({
  component_id: "red-port-new-world",
  gate_confidence: "chapter_to_verify",
  default_hidden: true,
}), false);

const descent = byId.get("fish-man-red-line-descent");
assert(descent?.animation_plan);
assert.equal(clip(descent, 601, "fishman_descent_route_state"), undefined);
assert.equal(clip(descent, 602, "fishman_descent_route_state")?.progress, 0);
assert.equal(clip(descent, 604, "fishman_descent_route_state")?.progress, .38);
assert.equal(clip(descent, 607, "fishman_descent_route_state")?.progress, 1);
assert.equal(clip(descent, 608, "fishman_descent_route_state"), undefined);
assert(clip(descent, 604, "fishman_current_cycle", 2416));
assert(clip(descent, 606, "fishman_volcanic_cycle", 2521));

let diveChapter = 601;
const diveVisible = makeNodeVisible(descent, () => diveChapter);
const sunny = {
  component_id: "coated-sunny-dive", reveal_chapter: 602,
  gate_confidence: "verified_state_window", default_hidden: true,
  active_through_chapter: 607.999,
};
assert.equal(diveVisible(sunny), false);
diveChapter = 602;
assert.equal(diveVisible(sunny), true);
diveChapter = 608;
assert.equal(diveVisible(sunny), false);

// The centreline remains the canonical 0/180 great circle, while the land
// footprint must contain real coastline variance instead of a fixed-width quad.
assert.equal(RED_LINE_LAND.features.length, 3);
const prime = RED_LINE_LAND.features.find((item) => item.properties?.id === "red-land-0");
assert(prime);
const ring = prime.geometry.coordinates[0];
const widths = new Set(ring.slice(0, 80).map(([lng]) => Math.round(Math.abs(lng) * 1000)));
assert(widths.size > 20, "Red Line land silhouette is still visually straight");
const equator = ring.filter(([, lat]) => Math.abs(lat) < .6);
assert(equator.some(([lng]) => lng < 0) && equator.some(([lng]) => lng > 0));

console.log("Dynamic geography runtime: PASS");
console.log("  Water 7: train, flood, Rocketman, and Enies waterfall tracks");
console.log("  Red Line: irregular continent silhouette and people-carrying Bondola");
console.log("  Fish-Man descent: chapter 602-607 vehicle, current, hazards, and trench");
