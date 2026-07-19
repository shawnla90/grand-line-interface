#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import { sampleRuntimeAnimation } from "../components/runtime-models.ts";

const payload = JSON.parse(fs.readFileSync(new URL("../data/generated/runtime_assets.json", import.meta.url)));
const byId = new Map(payload.assets.map((asset) => [asset.id, asset]));

assert.equal(payload._meta.counts.copied, 22);
assert.equal(payload._meta.counts.refused, 0);
assert.equal(byId.has("totto-land"), false);

const fishman = byId.get("fish-man-island");
assert.ok(fishman);
assert.equal(fishman.chapter_beats.base_reveal, 608);
assert.equal(fishman.chapter_beats.safe_full_scene, 608);
assert.equal(fishman.component_gates[0].reveal_chapter, 608);

const punk = byId.get("punk-hazard-geographic-system");
assert.ok(punk?.animation_plan);
assert.equal(sampleRuntimeAnimation(punk.animation_plan, 656, 2000, false), null);
const climate = sampleRuntimeAnimation(punk.animation_plan, 657, 2500, false);
assert.ok(climate);
assert.equal(climate.animate, true);
assert.deepEqual(climate.clips.map((clip) => clip.name), ["punk_hazard_environment_cycle"]);
const history = sampleRuntimeAnimation(punk.animation_plan, 658, 1979, false);
assert.ok(history);
assert.equal(history.animate, true);
assert.deepEqual(new Set(history.clips.map((clip) => clip.name)), new Set([
  "punk_hazard_duel_memory_fx",
  "punk_hazard_environment_cycle",
]));

const totto = byId.get("totto-land-food-geography");
assert.ok(totto?.animation_plan);
const route = sampleRuntimeAnimation(totto.animation_plan, 829, 2521, false);
assert.ok(route);
assert.equal(route.animate, true);
assert.deepEqual(route.clips.map((clip) => clip.name), ["totto_land_food_route_cycle"]);
assert.equal(sampleRuntimeAnimation(totto.animation_plan, 830, 2521, false), null);
const routeGate = totto.component_gates.find((gate) => gate.id === "totto-land-sea-route");
assert.deepEqual({
  reveal: routeGate.reveal_chapter,
  through: routeGate.active_through_chapter,
  verification: routeGate.verification,
  hidden: routeGate.default_hidden,
}, {
  reveal: 829,
  through: 829.999,
  verification: "verified_state_window",
  hidden: true,
});

console.log("Geography expansion runtime: PASS");
console.log("  Fish-Man Island full-model gate corrected to chapter 608");
console.log("  Punk Hazard climate persists from 657; historical FX joins only at 658");
console.log("  Totto Land foam route animates and remains visible only during chapter 829");
console.log("  old Totto Land runtime row is not registered beside its replacement");
