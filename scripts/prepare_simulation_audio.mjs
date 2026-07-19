#!/usr/bin/env node

/**
 * Freeze simulation-audio masters into browser-ready derivatives.
 *
 * The REGISTRY drives (data/simulation-audio-cues.json, hand-edited): for
 * every enabled cue this script finds its master, verifies its rights
 * receipt EXISTS before touching anything, renders a 48kHz metadata-stripped
 * MP3 to the cue's declared public src, and records both hashes in
 * public/audio/simulations/manifest.json — the provenance bridge the audit
 * cross-checks (the prepare_epic_audio.mjs posture).
 *
 * NORMALIZATION BY FAMILY, not one loudness for everything:
 *   - sfx/voice one-shots: PEAK normalize to -1.0 dBFS (a punch's crest is
 *     the point; flattening transients to a LUFS target kills them)
 *   - ambience/music loops + beds: EBU loudnorm (I=-18 music, -16 ambience,
 *     -16 voice beds), TP -1.5 — long material sits level under the scene
 *
 * Usage: node scripts/prepare_simulation_audio.mjs
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const projectRoot = resolve(import.meta.dirname, "..");
const mastersRoot = join(projectRoot, "assets/audio/simulations/masters");
const publicRoot = join(projectRoot, "public");
const registryPath = join(projectRoot, "data/simulation-audio-cues.json");
const manifestPath = join(projectRoot, "public/audio/simulations/manifest.json");

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.status !== 0) {
    console.error(result.stderr || result.stdout);
    process.exit(result.status ?? 1);
  }
  return `${result.stdout}\n${result.stderr}`;
}

function probe(path) {
  const raw = run("ffprobe", [
    "-v", "error",
    "-show_entries", "format=duration:stream=sample_rate,channels,codec_name",
    "-of", "json", path,
  ]);
  return JSON.parse(raw);
}

/** Measured peak in dBFS, via ffmpeg volumedetect. */
function peakDb(path) {
  const out = run("ffmpeg", ["-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"]);
  const match = out.match(/max_volume:\s*(-?[\d.]+) dB/);
  if (!match) {
    console.error(`volumedetect found no max_volume for ${path}`);
    process.exit(1);
  }
  return Number(match[1]);
}

const registry = JSON.parse(readFileSync(registryPath, "utf8"));
const files = [];
let prepared = 0;

for (const cue of registry.cues) {
  if (!cue.enabled) continue;
  // Only own-master cues are prepared here. OP-library and epic-journey srcs
  // are frozen by their own pipelines (ingest_op_soundboard / prepare_epic)
  // and cross-checked against their own manifests by the audit.
  if (!cue.src.startsWith("/audio/simulations/")) continue;
  const masterPath = join(mastersRoot, cue.source_file);
  if (!existsSync(masterPath)) {
    console.error(`${cue.id}: master missing: assets/audio/simulations/masters/${cue.source_file}`);
    process.exit(1);
  }
  // Rights BEFORE processing: no receipt, no derivative — full stop.
  if (!cue.receipt || !existsSync(join(projectRoot, cue.receipt))) {
    console.error(`${cue.id}: rights receipt missing (${cue.receipt ?? "null"}). Refusing to prepare.`);
    process.exit(1);
  }
  if (!cue.src.startsWith("/audio/simulations/")) {
    console.error(`${cue.id}: src must live under /audio/simulations/, got ${cue.src}`);
    process.exit(1);
  }

  const outPath = join(publicRoot, cue.src.replace(/^\//, ""));
  mkdirSync(dirname(outPath), { recursive: true });

  const isOneShot = cue.bus === "sfx" || (cue.bus === "voice" && !cue.loop);
  let filter;
  if (isOneShot) {
    const gain = -1.0 - peakDb(masterPath);
    filter = `volume=${gain.toFixed(2)}dB`;
  } else {
    const target = cue.bus === "score" ? -18 : -16;
    filter = `loudnorm=I=${target}:TP=-1.5:LRA=11`;
  }
  run("ffmpeg", [
    "-hide_banner", "-y",
    "-i", masterPath,
    "-af", filter,
    "-ar", "48000",
    "-ac", String(cue.channels),
    "-c:a", "libmp3lame", "-b:a", "160k",
    "-map_metadata", "-1",
    outPath,
  ]);

  const meta = probe(outPath);
  const durationMs = Math.round(Number(meta.format.duration) * 1000);
  files.push({
    id: cue.id,
    sourceFile: cue.source_file,
    sourceSha256: sha256(masterPath),
    publicPath: cue.src,
    publicSha256: sha256(outPath),
    durationMs,
    sampleRate: Number(meta.streams[0].sample_rate),
    channels: Number(meta.streams[0].channels),
    normalization: filter,
    rightsStatus: cue.rights_status,
    receipt: cue.receipt,
  });
  prepared += 1;
  console.log(`  [ok ] ${cue.id} → ${cue.src} (${durationMs}ms, ${filter})`);
}

mkdirSync(dirname(manifestPath), { recursive: true });
writeFileSync(manifestPath, `${JSON.stringify({ version: 1, files }, null, 2)}\n`);
console.log(`\nsimulation audio: ${prepared} derivatives frozen — wrote public/audio/simulations/manifest.json`);
console.log("Now run: npm run audit:sim-audio");
