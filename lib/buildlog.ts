/**
 * lib/buildlog.ts — the shipwright's log loader. Server-only (node:fs), same
 * contract as lib/schema.ts: validate at build time, THROW on violation.
 *
 * canon/build_log.json is hand-authored provenance about the BUILD, not the
 * story, so it deliberately does NOT flow through normalize.py or data/canon.json
 * — the data pipeline stays about One Piece. It is still canon/ (human-owned,
 * no script may write it) and still zod-gated on the way in.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

export const BuildLogEntry = z.object({
  phase: z.string(),
  title: z.string(),
  /** The model that did the work — "Claude Opus 4.8", "Codex", "Claude Fable 5". */
  builder: z.string(),
  harness: z.string(),
  role: z.string(),
  /** Short SHAs of the commits this phase landed as. Empty for plan-only entries. */
  commits: z.array(z.string()),
  /** Optional measured workload snapshot. Cached input is included in totalTokens. */
  usage: z
    .object({
      measuredAt: z.string(),
      inputTokens: z.number().int().nonnegative(),
      cachedInputTokens: z.number().int().nonnegative(),
      uncachedInputTokens: z.number().int().nonnegative(),
      outputTokens: z.number().int().nonnegative(),
      reasoningOutputTokens: z.number().int().nonnegative(),
      totalTokens: z.number().int().nonnegative(),
      note: z.string(),
    })
    .optional(),
  verified: z.boolean(),
});
export type BuildLogEntry = z.infer<typeof BuildLogEntry>;

export const BuildLog = z.object({ entries: z.array(BuildLogEntry) });
export type BuildLog = z.infer<typeof BuildLog>;

const BUILD_LOG_PATH = join(process.cwd(), "canon", "build_log.json");

let cached: BuildLog | null = null;

export function loadBuildLog(): BuildLog {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(BUILD_LOG_PATH, "utf8"));
  const parsed = BuildLog.safeParse(raw);
  if (!parsed.success) {
    throw new Error(
      `canon/build_log.json failed schema validation: ${parsed.error.issues
        .slice(0, 5)
        .map((i) => `${i.path.join(".")}: ${i.message}`)
        .join("; ")}`,
    );
  }
  cached = parsed.data;
  return cached;
}
