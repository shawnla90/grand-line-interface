#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const registry = JSON.parse(readFileSync(resolve(root, "data/epic-audio-cues.json"), "utf8"));
const manifest = JSON.parse(readFileSync(resolve(root, "public/audio/epic-journey/manifest.json"), "utf8"));
const failures = [];
const ids = new Set();
const sourceFiles = new Set();
const manifestBySource = new Map(manifest.files.map((file) => [file.originalName, file]));

if (!Number.isFinite(registry.cue_crossfade_ms) || registry.cue_crossfade_ms < 60 || registry.cue_crossfade_ms > 250) {
  failures.push("cue_crossfade_ms must be a short, audible-boundary smoothing window");
}

for (const cue of registry.cues) {
  if (ids.has(cue.id)) failures.push(`duplicate cue id: ${cue.id}`);
  ids.add(cue.id);
  if (sourceFiles.has(cue.source_file)) failures.push(`source used twice: ${cue.source_file}`);
  sourceFiles.add(cue.source_file);

  const asset = manifestBySource.get(cue.source_file);
  if (!asset) {
    failures.push(`${cue.id}: source missing from normalized manifest`);
    continue;
  }
  if (asset.publicPath !== cue.src) failures.push(`${cue.id}: public path drift`);
  if (Math.abs(asset.durationMs - cue.duration_ms) > 40) failures.push(`${cue.id}: duration drift`);
  if (!existsSync(resolve(root, cue.src.replace(/^\//, "public/")))) failures.push(`${cue.id}: public file missing`);
  if (cue.enabled !== false && cue.chapter == null) failures.push(`${cue.id}: enabled cue has no chapter gate`);
  if (cue.enabled === false && cue.verification !== "needs_identification") {
    failures.push(`${cue.id}: disabled cue lacks identification reason`);
  }
  if (cue.lane === "bed" && (!Number.isFinite(cue.lead_ms) || cue.lead_ms < 0)) {
    failures.push(`${cue.id}: bed cue needs non-negative lead_ms`);
  }
}

const cueById = new Map(registry.cues.map((cue) => [cue.id, cue]));
if (cueById.get("luffy-pirate-king")?.lane !== "bed") {
  failures.push("the long opening track must overlap the moving visual master as a bed");
}
for (const id of ["zoro-santoryu", "zoro-onigiri"]) {
  if (cueById.get(id)?.chapter !== 51) failures.push(`${id}: must land on the Mihawk duel at chapter 51`);
}

for (const asset of manifest.files) {
  if (!sourceFiles.has(asset.originalName)) failures.push(`normalized file not registered: ${asset.originalName}`);
  if (asset.outputSampleRate !== 48000 || asset.channels !== 2) {
    failures.push(`${asset.originalName}: browser format is not 48kHz stereo`);
  }
  if (asset.rightsStatus !== registry.rights_status) failures.push(`${asset.originalName}: rights status drift`);
}

if (failures.length) {
  console.error(failures.map((failure) => `FAIL ${failure}`).join("\n"));
  process.exit(1);
}

const active = registry.cues.filter((cue) => cue.enabled !== false);
const totalMs = active.reduce((sum, cue) => sum + cue.duration_ms, 0);
console.log(`epic audio: ${registry.cues.length} supplied, ${active.length} active, ${totalMs}ms active — PASS`);
