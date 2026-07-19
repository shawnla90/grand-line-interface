#!/usr/bin/env node

/** Focused headless audit for the simulation runtime's absolute-time rules. */

import assert from "node:assert/strict";
import {
  createReadyGatedSceneClock,
  markSceneClockReady,
  pauseSceneClock,
  resumeSceneClock,
  sceneClockElapsedMs,
  streakDisplacementAtAge,
} from "../lib/simulation.ts";

function checkReadyGate() {
  const clock = createReadyGatedSceneClock(100);
  assert.equal(sceneClockElapsedMs(clock, 5_000), 0, "loading time must hold authored t=0");

  markSceneClockReady(clock, 5_000, false);
  assert.equal(sceneClockElapsedMs(clock, 5_000), 0);
  assert.equal(sceneClockElapsedMs(clock, 6_200), 1_200);

  pauseSceneClock(clock, 6_200);
  assert.equal(sceneClockElapsedMs(clock, 20_000), 1_200, "hidden time must not advance");
  resumeSceneClock(clock, 20_300);
  assert.equal(sceneClockElapsedMs(clock, 20_800), 1_700);

  const hiddenLoad = createReadyGatedSceneClock(0);
  markSceneClockReady(hiddenLoad, 1_000, true);
  assert.equal(sceneClockElapsedMs(hiddenLoad, 9_000), 0, "ready-in-background starts paused");
  resumeSceneClock(hiddenLoad, 9_000);
  assert.equal(sceneClockElapsedMs(hiddenLoad, 9_500), 500);
}

function sampleStreakAtRate(hz, durationMs) {
  const step = 1_000 / hz;
  let value = 0;
  for (let age = 0; age < durationMs; age += step) {
    value = streakDisplacementAtAge(age, durationMs, 2, 1);
  }
  // Renderers commonly receive one final/clamped sample after the last
  // in-window frame. Its absolute result must not depend on prior call count.
  value = streakDisplacementAtAge(durationMs, durationMs, 2, 1);
  return value;
}

function checkRefreshRateIndependence() {
  for (const duration of [850, 1_400, 3_600]) {
    const byRate = [30, 60, 120].map((hz) => sampleStreakAtRate(hz, duration));
    assert.equal(byRate[0], byRate[1]);
    assert.equal(byRate[1], byRate[2]);

    const direct = streakDisplacementAtAge(300, duration, 2, -1);
    void streakDisplacementAtAge(900, duration, 2, -1);
    assert.equal(
      streakDisplacementAtAge(300, duration, 2, -1),
      direct,
      "backward sampling must rebuild the same absolute position",
    );
  }
}

checkReadyGate();
checkRefreshRateIndependence();
console.log("simulation runtime determinism: PASS (ready gate, pause/resume, 30/60/120 Hz, rewind)");
