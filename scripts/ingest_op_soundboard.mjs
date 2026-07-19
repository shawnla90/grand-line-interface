#!/usr/bin/env node

/**
 * Cut a YouTube soundboard into candidate clips; promote the accepted ones
 * into the OP clip library.
 *
 * Two commands, one human between them:
 *
 *   discover  — download the video's audio ONCE into gitignored staging,
 *               cut every embedded chapter (or, when the video has none,
 *               every silence-bounded span) into candidate clips, and write
 *               data/review/op-soundboard-<slug>.candidates.json for a human
 *               to listen through and label. Nothing leaves staging.
 *
 *   promote   — given the human's curated list, copy each accepted candidate
 *               into assets/audio/op-library/<video-slug>/ as the frozen
 *               master, render the normalized public derivative under
 *               /audio/op-library/, merge public/audio/op-library/manifest.json
 *               (the provenance bridge the audit cross-checks), and write
 *               ready-to-paste registry rows to
 *               data/review/op-soundboard-<slug>.proposals.json.
 *
 * The registry (data/simulation-audio-cues.json) stays HAND-EDITED — this
 * tool only proposes rows, it never touches the registry. Every clip is
 * ripped One Piece material: rights_status is local_prototype_only, always,
 * and the audit pins any /audio/op-library/ src to exactly that. The release
 * wall (audit:sim-audio --release) keeps all of it out of production.
 *
 * Chapter marks are editorial (±0.5s vs the audio), so every cut is padded
 * then silence-trimmed; long chapters holding several hits are sub-segmented
 * by their silence gaps into separate candidates.
 *
 * Usage:
 *   node scripts/ingest_op_soundboard.mjs discover --url <youtube-url> --video-slug <slug>
 *   node scripts/ingest_op_soundboard.mjs promote --video-slug <slug> \
 *     --accept data/review/op-soundboard-<slug>.curated.json
 */

import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const projectRoot = resolve(import.meta.dirname, "..");
const libraryRoot = join(projectRoot, "assets/audio/op-library");
const stagingRoot = join(libraryRoot, "_staging");
const publicRoot = join(projectRoot, "public/audio/op-library");
const reviewRoot = join(projectRoot, "data/review");

/** Padding around editorial chapter marks before silence-trimming. */
const CUT_PAD_S = 0.15;
/** silencedetect tuning: what counts as silence, and for how long. */
const SILENCE_DB = -32;
const SILENCE_MIN_S = 0.3;
/** Spans closer than this merge into one candidate (breaths inside one hit). */
const SPAN_MERGE_S = 0.25;
/** Spans shorter than this are detection noise, not clips. */
const SPAN_MIN_S = 0.15;

function fail(message) {
  console.error(message);
  process.exit(1);
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) {
    console.error(result.stderr || result.stdout);
    process.exit(result.status ?? 1);
  }
  return `${result.stdout}\n${result.stderr}`;
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function probe(path) {
  const raw = run("ffprobe", [
    "-v", "error",
    "-show_entries", "format=duration:stream=sample_rate,channels,codec_name",
    "-of", "json", path,
  ]);
  return JSON.parse(raw);
}

/** Measured peak in dBFS, via ffmpeg volumedetect (the prepare-script recipe). */
function peakDb(path) {
  const out = run("ffmpeg", ["-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"]);
  const match = out.match(/max_volume:\s*(-?[\d.]+) dB/);
  if (!match) fail(`volumedetect found no max_volume for ${path}`);
  return Number(match[1]);
}

function slugify(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * Non-silent spans of source within [start, end], in absolute seconds.
 * silencedetect reports times relative to the seek point, so the window
 * start is added back. Adjacent spans separated by tiny gaps merge; spans
 * too short to be a clip drop.
 */
function nonSilentSpans(sourcePath, start, end) {
  const out = run("ffmpeg", [
    "-hide_banner",
    "-ss", start.toFixed(3),
    "-t", (end - start).toFixed(3),
    "-i", sourcePath,
    "-af", `silencedetect=noise=${SILENCE_DB}dB:d=${SILENCE_MIN_S}`,
    "-f", "null", "-",
  ]);
  const silences = [];
  let openStart = null;
  for (const line of out.split("\n")) {
    const s = line.match(/silence_start:\s*(-?[\d.]+)/);
    const e = line.match(/silence_end:\s*(-?[\d.]+)/);
    if (s) openStart = Number(s[1]) + start;
    if (e && openStart !== null) {
      silences.push([openStart, Number(e[1]) + start]);
      openStart = null;
    }
  }
  if (openStart !== null) silences.push([openStart, end]);

  const spans = [];
  let cursor = start;
  for (const [s, e] of silences) {
    if (s > cursor) spans.push([cursor, Math.min(s, end)]);
    cursor = Math.max(cursor, e);
  }
  if (cursor < end) spans.push([cursor, end]);

  const merged = [];
  for (const span of spans) {
    const last = merged[merged.length - 1];
    if (last && span[0] - last[1] < SPAN_MERGE_S) last[1] = span[1];
    else merged.push([...span]);
  }
  return merged.filter(([s, e]) => e - s >= SPAN_MIN_S);
}

function cutClip(sourcePath, outPath, start, end) {
  mkdirSync(dirname(outPath), { recursive: true });
  // Stream copy — the source is already lossy; cuts land on AAC packet
  // boundaries (~21ms), inside the pad that silence-trimming already ate.
  run("ffmpeg", [
    "-hide_banner", "-loglevel", "error", "-y",
    "-i", sourcePath,
    "-ss", start.toFixed(3),
    "-to", end.toFixed(3),
    "-c", "copy",
    outPath,
  ]);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i].startsWith("--") || argv[i + 1] === undefined) {
      fail(`bad argument pair at "${argv[i]}"`);
    }
    args[argv[i].slice(2)] = argv[i + 1];
  }
  return args;
}

function discover({ url, "video-slug": videoSlug }) {
  if (!url || !videoSlug) fail("discover needs --url and --video-slug");
  if (videoSlug !== slugify(videoSlug)) fail(`--video-slug must be a slug, got "${videoSlug}"`);

  const stagingDir = join(stagingRoot, videoSlug);
  mkdirSync(stagingDir, { recursive: true });

  console.log(`[meta] ${url}`);
  const meta = JSON.parse(run("yt-dlp", ["-J", "--no-warnings", url]));
  const chapters = meta.chapters ?? [];

  const sourcePath = join(stagingDir, "source.m4a");
  if (existsSync(sourcePath)) {
    console.log("[dl  ] source.m4a already staged — skipping download");
  } else {
    console.log("[dl  ] downloading audio track…");
    run("yt-dlp", [
      "-x", "--audio-format", "m4a", "--no-warnings",
      "-o", join(stagingDir, "source.%(ext)s"),
      url,
    ]);
    if (!existsSync(sourcePath)) fail("download did not produce source.m4a");
  }
  const duration = Number(probe(sourcePath).format.duration);

  const candidatesDir = join(stagingDir, "candidates");
  mkdirSync(candidatesDir, { recursive: true });

  const candidates = [];
  const emit = (start, end, chapterTitle, index, subIndex, subCount) => {
    const base = chapterTitle
      ? slugify(chapterTitle)
      : `unlabeled-${String(index).padStart(2, "0")}`;
    const name =
      subCount > 1
        ? `c${String(index).padStart(2, "0")}-${base}-${subIndex + 1}.m4a`
        : `c${String(index).padStart(2, "0")}-${base}.m4a`;
    const outPath = join(candidatesDir, name);
    cutClip(sourcePath, outPath, start, end);
    candidates.push({
      file: `candidates/${name}`,
      chapterTitle: chapterTitle ?? null,
      suggestedSlug: chapterTitle ? `op-sfx-${slugify(chapterTitle)}` : "UNLABELED — needs human identification",
      start: Number(start.toFixed(3)),
      end: Number(end.toFixed(3)),
      durationMs: Math.round((end - start) * 1000),
    });
  };

  if (chapters.length > 0) {
    console.log(`[cut ] ${chapters.length} embedded chapters — padding ${CUT_PAD_S}s, silence-trimming each`);
    chapters.forEach((chapter, index) => {
      const winStart = Math.max(0, chapter.start_time - CUT_PAD_S);
      const winEnd = Math.min(duration, chapter.end_time + CUT_PAD_S);
      const spans = nonSilentSpans(sourcePath, winStart, winEnd);
      if (spans.length === 0) {
        console.log(`  [skip] ${chapter.title} — silent window`);
        return;
      }
      spans.forEach((span, subIndex) => emit(span[0], span[1], chapter.title, index, subIndex, spans.length));
    });
  } else {
    console.log("[cut ] no chapters — segmenting the whole file by silence; SPEAKER IDENTITY IS UNASSIGNED");
    const spans = nonSilentSpans(sourcePath, 0, duration);
    spans.forEach((span, index) => emit(span[0], span[1], null, index, 0, 1));
  }

  mkdirSync(reviewRoot, { recursive: true });
  const reviewPath = join(reviewRoot, `op-soundboard-${videoSlug}.candidates.json`);
  writeFileSync(
    reviewPath,
    `${JSON.stringify(
      {
        videoSlug,
        videoId: meta.id,
        videoTitle: meta.title,
        url,
        durationS: Number(duration.toFixed(1)),
        _next:
          "Listen through staging candidates, then write a curated JSON " +
          "([{candidate, clip_slug, kind, bus, family, max_voices}]) and run promote. " +
          "Unlabeled candidates need a human to name the speaker — never guess.",
        candidates,
      },
      null,
      2,
    )}\n`,
  );
  console.log(`\ndiscover: ${candidates.length} candidates in ${join("assets/audio/op-library/_staging", videoSlug, "candidates")}`);
  console.log(`review file: data/review/op-soundboard-${videoSlug}.candidates.json`);
}

function promote({ "video-slug": videoSlug, accept }) {
  if (!videoSlug || !accept) fail("promote needs --video-slug and --accept");
  const stagingDir = join(stagingRoot, videoSlug);
  const candidatesPath = join(reviewRoot, `op-soundboard-${videoSlug}.candidates.json`);
  if (!existsSync(candidatesPath)) fail(`no candidates file — run discover first (${candidatesPath})`);
  const discovered = JSON.parse(readFileSync(candidatesPath, "utf8"));
  const byFile = new Map(discovered.candidates.map((c) => [c.file, c]));

  const curated = JSON.parse(readFileSync(resolve(accept), "utf8"));
  if (!Array.isArray(curated) || curated.length === 0) fail("curated file must be a non-empty array");

  const manifestPath = join(publicRoot, "manifest.json");
  const manifest = existsSync(manifestPath)
    ? JSON.parse(readFileSync(manifestPath, "utf8"))
    : { version: 1, files: [] };
  const manifestBySlug = new Map(manifest.files.map((f) => [f.clipSlug, f]));

  const proposals = [];
  for (const entry of curated) {
    const { candidate, clip_slug: clipSlug, kind, bus, family, max_voices: maxVoices } = entry;
    const info = byFile.get(candidate);
    if (!info) fail(`curated candidate not in discover output: ${candidate}`);
    if (!clipSlug || clipSlug !== slugify(clipSlug)) fail(`bad clip_slug "${clipSlug}"`);
    if (!["sfx", "voice"].includes(kind)) fail(`${clipSlug}: kind must be sfx|voice`);
    if (!["sfx", "voice", "score", "ambience"].includes(bus)) fail(`${clipSlug}: bad bus "${bus}"`);
    if (!family) fail(`${clipSlug}: family required`);
    if (!Number.isInteger(maxVoices) || maxVoices < 1 || maxVoices > 4) fail(`${clipSlug}: max_voices must be 1..4`);

    const candidatePath = join(stagingDir, candidate);
    if (!existsSync(candidatePath)) fail(`staged candidate missing: ${candidatePath} — re-run discover`);

    // Freeze the master: the accepted cut (optionally trimmed — some chapters
    // are long continuous beds and the cue wants only the head), reviewable.
    const masterRel = `${videoSlug}/${clipSlug}.m4a`;
    const masterPath = join(libraryRoot, masterRel);
    mkdirSync(dirname(masterPath), { recursive: true });
    if (Array.isArray(entry.trim_ms)) {
      const [trimStart, trimEnd] = entry.trim_ms;
      if (!(trimEnd > trimStart) || trimStart < 0) fail(`${clipSlug}: bad trim_ms`);
      cutClip(candidatePath, masterPath, trimStart / 1000, trimEnd / 1000);
    } else {
      copyFileSync(candidatePath, masterPath);
    }

    // Render the derivative: one-shots keep their transient crest
    // (peak −1 dBFS); anything looping sits at a level (−16 LUFS).
    const isOneShot = !entry.loop;
    const filter = isOneShot
      ? `volume=${(-1.0 - peakDb(masterPath)).toFixed(2)}dB`
      : "loudnorm=I=-16:TP=-1.5:LRA=11";
    const publicRel = `/audio/op-library/${clipSlug}.mp3`;
    const outPath = join(projectRoot, "public", publicRel.replace(/^\//, ""));
    mkdirSync(dirname(outPath), { recursive: true });
    run("ffmpeg", [
      "-hide_banner", "-loglevel", "error", "-y",
      "-i", masterPath,
      "-af", filter,
      "-ar", "48000", "-ac", "2",
      "-c:a", "libmp3lame", "-b:a", "160k",
      "-map_metadata", "-1",
      outPath,
    ]);

    const outMeta = probe(outPath);
    const durationMs = Math.round(Number(outMeta.format.duration) * 1000);
    manifestBySlug.set(clipSlug, {
      clipSlug,
      videoId: discovered.videoId,
      videoTitle: discovered.videoTitle,
      chapter: info.chapterTitle
        ? { title: info.chapterTitle, start: info.start, end: info.end }
        : null,
      cutRange: { start: info.start, end: info.end },
      sourceFile: `assets/audio/op-library/${masterRel}`,
      sourceSha256: sha256(masterPath),
      publicPath: publicRel,
      publicSha256: sha256(outPath),
      durationMs,
      sampleRate: Number(outMeta.streams[0].sample_rate),
      channels: Number(outMeta.streams[0].channels),
      normalization: filter,
      rightsStatus: "local_prototype_only",
    });

    proposals.push({
      id: clipSlug,
      source_file: masterRel,
      src: publicRel,
      kind,
      bus,
      family,
      duration_ms: durationMs,
      sample_rate: 48000,
      channels: 2,
      source: "op-clip-library",
      license: "unlicensed-one-piece-clip",
      rights_status: "local_prototype_only",
      receipt: null,
      attribution: null,
      max_voices: maxVoices,
      loop: Boolean(entry.loop),
      enabled: true,
    });
    console.log(`  [ok ] ${clipSlug} ← ${candidate} (${durationMs}ms, ${filter})`);
  }

  manifest.files = [...manifestBySlug.values()].sort((a, b) => a.clipSlug.localeCompare(b.clipSlug));
  mkdirSync(publicRoot, { recursive: true });
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

  proposals.sort((a, b) => a.id.localeCompare(b.id));
  const proposalsPath = join(reviewRoot, `op-soundboard-${videoSlug}.proposals.json`);
  writeFileSync(proposalsPath, `${JSON.stringify(proposals, null, 2)}\n`);

  console.log(`\npromote: ${proposals.length} clips frozen — manifest at public/audio/op-library/manifest.json`);
  console.log(`registry rows to hand-curate: data/review/op-soundboard-${videoSlug}.proposals.json`);
  console.log("Paste accepted rows into data/simulation-audio-cues.json, then: npm run audit:sim-audio");
}

const [command, ...rest] = process.argv.slice(2);
const args = parseArgs(rest);
if (command === "discover") discover(args);
else if (command === "promote") promote(args);
else fail("usage: ingest_op_soundboard.mjs <discover|promote> --…");
