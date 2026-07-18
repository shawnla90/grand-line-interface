import type { EpicAudioCue } from "@/config/epic-audio-cues";
import type { Journey } from "@/lib/journey";

type EpicSegment = {
  t0: number;
  t1: number;
  fromProgress: number;
  toProgress: number;
  cue: EpicAudioCue | null;
};

export type EpicJourneySample = {
  progress: number;
  cue: EpicAudioCue | null;
  cueElapsedMs: number;
  done: boolean;
};

export type EpicJourneyTimeline = {
  durationMs: number;
  sampleAt: (elapsedMs: number) => EpicJourneySample;
  cueCount: number;
};

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

/** First timeline position whose revealed chapter is at least `chapter`. */
function progressForChapter(journey: Journey, chapter: number): number {
  if (chapter <= journey.chapterAt(0)) return 0;
  if (chapter >= journey.chapterAt(1)) return 1;
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 42; i += 1) {
    const mid = (lo + hi) / 2;
    if (journey.chapterAt(mid) < chapter) lo = mid;
    else hi = mid;
  }
  return hi;
}

/**
 * Stretch the existing visual shot list around the supplied audio. Travel
 * keeps its own fixed budget; each cue contributes its full duration. A cue
 * may advance through a small chapter range, so long dialogue and music keep
 * the ship moving instead of freezing the map.
 */
export function buildEpicJourneyTimeline(
  journey: Journey,
  cues: EpicAudioCue[],
  travelBudgetMs: number,
  cueGapMs: number,
): EpicJourneyTimeline {
  const active = cues
    .filter((cue): cue is EpicAudioCue & { chapter: number } => cue.enabled && cue.chapter !== null)
    .toSorted((a, b) => a.chapter - b.chapter || a.order - b.order);

  const segments: EpicSegment[] = [];
  let cursorProgress = 0;
  let cursorMs = 0;

  const push = (durationMs: number, fromProgress: number, toProgress: number, cue: EpicAudioCue | null) => {
    if (durationMs <= 0) return;
    segments.push({
      t0: cursorMs,
      t1: cursorMs + durationMs,
      fromProgress: clamp01(fromProgress),
      toProgress: clamp01(toProgress),
      cue,
    });
    cursorMs += durationMs;
  };

  for (const cue of active) {
    const anchor = Math.max(cursorProgress, progressForChapter(journey, cue.chapter));
    if (anchor > cursorProgress) {
      push((anchor - cursorProgress) * travelBudgetMs, cursorProgress, anchor, null);
    }

    const cueEnd = cue.chapterEnd == null
      ? anchor
      : Math.max(anchor, progressForChapter(journey, cue.chapterEnd));
    push(cue.durationMs + cueGapMs, anchor, cueEnd, cue);
    cursorProgress = cueEnd;
  }

  if (cursorProgress < 1) {
    push((1 - cursorProgress) * travelBudgetMs, cursorProgress, 1, null);
  }

  const durationMs = Math.max(1, cursorMs);
  const sampleAt = (elapsedMs: number): EpicJourneySample => {
    const elapsed = Math.max(0, Math.min(durationMs, elapsedMs));
    const segment = segments.find((candidate) => elapsed <= candidate.t1) ?? segments.at(-1);
    if (!segment) return { progress: 1, cue: null, cueElapsedMs: 0, done: true };
    const width = Math.max(1, segment.t1 - segment.t0);
    const u = clamp01((elapsed - segment.t0) / width);
    return {
      progress: segment.fromProgress + (segment.toProgress - segment.fromProgress) * u,
      cue: segment.cue,
      cueElapsedMs: segment.cue ? Math.max(0, elapsed - segment.t0) : 0,
      done: elapsedMs >= durationMs,
    };
  };

  return { durationMs, sampleAt, cueCount: active.length };
}
