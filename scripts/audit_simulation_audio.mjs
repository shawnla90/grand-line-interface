#!/usr/bin/env node

/**
 * Gate the simulation-audio registry against the frozen derivatives and the
 * compiled playback bindings — the audit_epic_audio.mjs posture, extended
 * with the RELEASE rights gate.
 *
 * Default mode (npm run audit:sim-audio): structural truth. Every enabled
 * cue has a manifest row, an on-disk derivative whose hash matches, 48kHz
 * audio, a duration within 40ms of the registry's claim, an existing rights
 * receipt, and attribution when its license demands it. Every compiled
 * playback binding points at an enabled cue.
 *
 * --release: the shipping gate. Enabled cues must be `cleared`, or
 * `attribution_required` WITH attribution (which also emits
 * public/audio/simulations/attribution.json). `local_prototype_only` and
 * `blocked` fail the build — prototype material cannot reach production.
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";

const projectRoot = resolve(import.meta.dirname, "..");
const release = process.argv.includes("--release");

const registry = JSON.parse(readFileSync(join(projectRoot, "data/simulation-audio-cues.json"), "utf8"));
const playback = JSON.parse(readFileSync(join(projectRoot, "data/generated/story_scene_playback.json"), "utf8"));
const manifestPath = join(projectRoot, "public/audio/simulations/manifest.json");
const manifest = existsSync(manifestPath)
  ? JSON.parse(readFileSync(manifestPath, "utf8"))
  : { version: 1, files: [] };
const manifestById = new Map(manifest.files.map((f) => [f.id, f]));

const problems = [];
const seen = new Set();

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

for (const cue of registry.cues) {
  const where = `cue ${cue.id}`;
  if (seen.has(cue.id)) problems.push(`${where}: duplicate id`);
  seen.add(cue.id);
  if (!cue.enabled) continue;

  const entry = manifestById.get(cue.id);
  if (!entry) {
    problems.push(`${where}: enabled but not prepared (no manifest row) — run prepare_simulation_audio.mjs`);
    continue;
  }
  const publicFile = join(projectRoot, "public", cue.src.replace(/^\//, ""));
  if (!existsSync(publicFile)) {
    problems.push(`${where}: derivative missing on disk: ${cue.src}`);
    continue;
  }
  if (entry.publicPath !== cue.src) problems.push(`${where}: manifest path ${entry.publicPath} != registry src ${cue.src}`);
  if (sha256(publicFile) !== entry.publicSha256) problems.push(`${where}: derivative hash drifted from manifest`);
  if (entry.sampleRate !== 48000) problems.push(`${where}: derivative is ${entry.sampleRate}Hz, not 48000`);
  if (entry.channels !== cue.channels) problems.push(`${where}: derivative has ${entry.channels}ch, registry says ${cue.channels}`);
  if (Math.abs(entry.durationMs - cue.duration_ms) > 40) {
    problems.push(`${where}: duration ${entry.durationMs}ms drifts >40ms from registry ${cue.duration_ms}ms`);
  }
  if (entry.rightsStatus !== cue.rights_status) problems.push(`${where}: manifest rights ${entry.rightsStatus} != registry ${cue.rights_status}`);
  if (!cue.receipt || !existsSync(join(projectRoot, cue.receipt))) {
    problems.push(`${where}: rights receipt missing (${cue.receipt ?? "null"})`);
  }
  if (cue.rights_status === "attribution_required" && !cue.attribution) {
    problems.push(`${where}: attribution_required without attribution text`);
  }
  if (release && !["cleared", "attribution_required"].includes(cue.rights_status)) {
    problems.push(`${where}: RELEASE GATE — rights_status ${cue.rights_status} cannot ship`);
  }
}

// Every compiled binding must resolve to an enabled cue.
const enabledIds = new Set(registry.cues.filter((c) => c.enabled).map((c) => c.id));
for (const scene of playback.scenes) {
  for (const binding of scene.audio) {
    if (!enabledIds.has(binding.cue_id)) {
      problems.push(`scene ${scene.scene_id} binding ${binding.id}: cue ${binding.cue_id} is not an enabled registry cue`);
    }
  }
}

// Orphan check: a prepared derivative whose registry row vanished is stale bytes.
for (const entry of manifest.files) {
  if (!registry.cues.some((c) => c.id === entry.id)) {
    problems.push(`manifest ${entry.id}: no registry row (stale derivative — remove or re-register)`);
  }
}

if (release) {
  const attributions = registry.cues
    .filter((c) => c.enabled && c.rights_status === "attribution_required")
    .map((c) => ({ id: c.id, license: c.license, attribution: c.attribution }));
  writeFileSync(
    join(projectRoot, "public/audio/simulations/attribution.json"),
    `${JSON.stringify({ version: 1, attributions }, null, 2)}\n`,
  );
}

if (problems.length) {
  console.error(`simulation audio: ${problems.length} problem(s):`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}

const enabled = registry.cues.filter((c) => c.enabled);
const totalMs = enabled.reduce((a, c) => a + c.duration_ms, 0);
const bindings = playback.scenes.reduce((a, s) => a + s.audio.length, 0);
console.log(
  `simulation audio: ${registry.cues.length} cues, ${enabled.length} enabled, ${bindings} bindings, ${totalMs}ms enabled audio${release ? " — RELEASE GATE" : ""} — PASS`,
);
