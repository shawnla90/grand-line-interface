#!/usr/bin/env node

/**
 * Generate ORIGINAL simulation sound masters through the ElevenLabs Sound
 * Effects API — an OFFLINE build tool, never a runtime dependency. The
 * browser plays only checked-in, hashed derivatives; no API key or external
 * audio URL can reach the client bundle from here.
 *
 * Input: a briefs JSON — an array of functional sound descriptions:
 *   [{ "id": "heavy-fleet-impact-01",
 *      "prompt": "one massive wooden ship hull impact, deep, dry, no music",
 *      "duration_s": 1.5, "prompt_influence": 0.6 }]
 *
 * Every accepted generation writes TWO files:
 *   assets/audio/simulations/masters/<id>.mp3        (the frozen master)
 *   assets/audio/licenses/elevenlabs/<id>.json       (the receipt: request,
 *     response metadata, sha256, timestamp — the rights paper trail the
 *     registry's `receipt` field points at)
 *
 * The cue registry (data/simulation-audio-cues.json) stays HAND-EDITED —
 * generation proposes files; a human curates rows, gains, and rights status.
 *
 * Usage:
 *   ELEVENLABS_API_KEY=... node scripts/generate_simulation_audio.mjs briefs.json [--only id1,id2]
 *   (key: `sqlite3 ~/.niobot/data/niobot.db "SELECT value FROM secrets WHERE key='ELEVENLABS_API_KEY'"`)
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";

const API_URL = "https://api.elevenlabs.io/v1/sound-generation";

const apiKey = process.env.ELEVENLABS_API_KEY;
if (!apiKey) {
  console.error("ELEVENLABS_API_KEY is not set. Refusing to run.");
  process.exit(2);
}

const briefsPath = process.argv[2];
if (!briefsPath) {
  console.error("usage: node scripts/generate_simulation_audio.mjs <briefs.json> [--only id1,id2]");
  process.exit(2);
}

const onlyFlag = process.argv.indexOf("--only");
const only = onlyFlag !== -1 ? new Set(process.argv[onlyFlag + 1].split(",")) : null;

const projectRoot = resolve(import.meta.dirname, "..");
const mastersRoot = join(projectRoot, "assets/audio/simulations/masters");
const receiptsRoot = join(projectRoot, "assets/audio/licenses/elevenlabs");
mkdirSync(mastersRoot, { recursive: true });
mkdirSync(receiptsRoot, { recursive: true });

const briefs = JSON.parse(readFileSync(resolve(briefsPath), "utf8"));

let generated = 0;
let skipped = 0;

for (const brief of briefs) {
  const { id, prompt } = brief;
  if (!id || !prompt) {
    console.error(`brief missing id/prompt: ${JSON.stringify(brief)}`);
    process.exit(1);
  }
  if (only && !only.has(id)) continue;
  const masterPath = join(mastersRoot, `${id}.mp3`);
  if (existsSync(masterPath)) {
    // A frozen master is never silently regenerated — delete it on purpose
    // to re-roll, so the hash trail stays intentional.
    console.log(`  [skip] ${id} — master already frozen`);
    skipped += 1;
    continue;
  }

  const body = {
    text: prompt,
    duration_seconds: brief.duration_s ?? undefined,
    prompt_influence: brief.prompt_influence ?? 0.55,
  };
  console.log(`  [gen ] ${id} — "${prompt.slice(0, 60)}..."`);
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "xi-api-key": apiKey, "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    console.error(`  ElevenLabs ${res.status} for ${id}: ${(await res.text()).slice(0, 300)}`);
    process.exit(1);
  }
  const audio = Buffer.from(await res.arrayBuffer());
  writeFileSync(masterPath, audio);
  const receipt = {
    provider: "elevenlabs",
    endpoint: API_URL,
    generated_at: new Date().toISOString(),
    request: body,
    response: {
      status: res.status,
      content_type: res.headers.get("content-type"),
      request_id: res.headers.get("request-id") ?? res.headers.get("x-request-id"),
      history_item_id: res.headers.get("history-item-id"),
    },
    master: `assets/audio/simulations/masters/${id}.mp3`,
    master_sha256: createHash("sha256").update(audio).digest("hex"),
    note: "Original generated output. Usable commercially only under the account's active paid-plan terms at generation time — confirm tier before flipping rights_status to cleared.",
  };
  writeFileSync(join(receiptsRoot, `${id}.json`), `${JSON.stringify(receipt, null, 2)}\n`);
  generated += 1;
}

console.log(`\nsimulation audio: ${generated} generated, ${skipped} already frozen.`);
console.log("Next: curate rows in data/simulation-audio-cues.json, then run scripts/prepare_simulation_audio.mjs");
