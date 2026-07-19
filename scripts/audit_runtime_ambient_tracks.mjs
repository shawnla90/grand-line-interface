#!/usr/bin/env node

import assert from "node:assert/strict";
import { sampleRuntimeAnimation } from "../components/runtime-models.ts";

const plan = {
  clock: "chapter_entry_elapsed_ms",
  reduced_motion: "freeze neutral environmental motion at its authored rest pose",
  chapter_states: [],
  ambient_tracks: [{
    channel: "punk_hazard_weather",
    name: "punk_hazard_environment_cycle",
    active_from_chapter: 655,
    active_through_chapter: 699,
    duration_ms: 4000,
    loop: true,
  }],
};

assert.equal(sampleRuntimeAnimation(plan, 654, 2500, false), null);

const live = sampleRuntimeAnimation(plan, 655, 2500, false);
assert.ok(live);
assert.equal(live.animate, true);
assert.deepEqual(live.clips, [{
  name: "punk_hazard_environment_cycle",
  progress: 0.625,
  loop: true,
}]);

const reduced = sampleRuntimeAnimation(plan, 699, 2500, true);
assert.ok(reduced);
assert.equal(reduced.animate, false);
assert.deepEqual(reduced.clips, [{
  name: "punk_hazard_environment_cycle",
  progress: 0,
  loop: true,
}]);

assert.equal(sampleRuntimeAnimation(plan, 700, 2500, false), null);

console.log("Runtime ambient tracks: PASS");
console.log("  active chapter windows loop neutral island effects");
console.log("  reduced motion freezes the authored rest pose");
console.log("  outside the chapter window no clip is sampled");
