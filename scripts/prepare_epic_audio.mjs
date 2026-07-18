#!/usr/bin/env node

/**
 * Freeze Shawn's supplied Grand Line audio and create browser-ready copies.
 *
 * Originals remain byte-for-byte under assets/audio/epic-journey so their
 * hashes are reviewable. Public derivatives are normalized to one browser
 * format; the checked manifest is the provenance bridge between the two.
 *
 * Usage:
 *   node scripts/prepare_epic_audio.mjs \
 *     "/Users/shawnos.ai/Downloads/op audio file for glc project"
 */

import { copyFileSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, extname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const sourceRoot = resolve(process.argv[2] ?? "");
if (!process.argv[2]) {
  console.error("usage: node scripts/prepare_epic_audio.mjs <source-directory>");
  process.exit(2);
}

const projectRoot = resolve(import.meta.dirname, "..");
const originalsRoot = join(projectRoot, "assets/audio/epic-journey");
const publicRoot = join(projectRoot, "public/audio/epic-journey");

const MUSIC = new Set([
  "One-Piece-Wano-Theme.mp3",
  "one-piece-overtaken-ost.mp3",
  "one-piece-overtaken.mp3",
]);

function slugify(name) {
  return basename(name, extname(name))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.status !== 0) {
    console.error(result.stderr || result.stdout);
    process.exit(result.status ?? 1);
  }
  return result.stdout.trim();
}

function probe(path) {
  return JSON.parse(
    run("ffprobe", [
      "-v", "error",
      "-show_entries", "format=duration:stream=sample_rate,channels,codec_name",
      "-of", "json",
      path,
    ]),
  );
}

mkdirSync(originalsRoot, { recursive: true });
mkdirSync(publicRoot, { recursive: true });

const files = readdirSync(sourceRoot)
  .filter((name) => extname(name).toLowerCase() === ".mp3")
  .sort((a, b) => a.localeCompare(b));

const manifest = [];
for (const originalName of files) {
  const kind = MUSIC.has(originalName) ? "music" : "voice";
  const frozenDir = join(originalsRoot, kind);
  mkdirSync(frozenDir, { recursive: true });

  const sourcePath = join(sourceRoot, originalName);
  const frozenPath = join(frozenDir, originalName);
  const outputName = `${slugify(originalName)}.mp3`;
  const publicPath = join(publicRoot, outputName);
  copyFileSync(sourcePath, frozenPath);

  const integratedLufs = kind === "music" ? -18 : -16;
  run("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y",
    "-i", frozenPath,
    "-map_metadata", "-1",
    "-af", `loudnorm=I=${integratedLufs}:TP=-1.5:LRA=11`,
    "-ar", "48000", "-ac", "2",
    "-codec:a", "libmp3lame", "-b:a", "160k",
    publicPath,
  ]);

  const sourceMeta = probe(frozenPath);
  const outputMeta = probe(publicPath);
  manifest.push({
    originalName,
    kind,
    source: `assets/audio/epic-journey/${kind}/${originalName}`,
    sourceSha256: sha256(frozenPath),
    publicPath: `/audio/epic-journey/${outputName}`,
    publicSha256: sha256(publicPath),
    durationMs: Math.round(Number(outputMeta.format.duration) * 1000),
    sourceCodec: sourceMeta.streams[0]?.codec_name ?? null,
    sourceSampleRate: Number(sourceMeta.streams[0]?.sample_rate ?? 0),
    outputSampleRate: Number(outputMeta.streams[0]?.sample_rate ?? 0),
    channels: Number(outputMeta.streams[0]?.channels ?? 0),
    normalization: { integratedLufs, truePeakDb: -1.5, loudnessRange: 11 },
    rightsStatus: "local_prototype_only",
  });
}

writeFileSync(
  join(publicRoot, "manifest.json"),
  `${JSON.stringify({ version: 1, files: manifest }, null, 2)}\n`,
);

console.log(`prepared ${manifest.length} epic-journey audio files`);
