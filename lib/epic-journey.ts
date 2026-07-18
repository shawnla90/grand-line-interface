import type { EpicAudioCue } from "@/config/epic-audio-cues";
import type { Journey } from "@/lib/journey";

type EpicVisualSegment = {
  t0: number;
  t1: number;
  fromProgress: number;
  toProgress: number;
};

type EpicAudioSegment = {
  t0: number;
  t1: number;
  cue: EpicAudioCue;
};

export type EpicCuePlayback = {
  cue: EpicAudioCue;
  cueElapsedMs: number;
};

export type EpicJourneySample = {
  progress: number;
  /** The foreground cue used by the caption UI, falling back to the bed. */
  cue: EpicAudioCue | null;
  cueElapsedMs: number;
  /** Every simultaneous lane the audio player should keep in sync. */
  audio: EpicCuePlayback[];
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
 * Last position still held at `chapter`. A plain travel crossing has a
 * zero-width range; a journey story stop has a real range. Epic must traverse
 * that range or it parks on the first frame of the scene forever.
 */
function progressAfterChapter(journey: Journey, chapter: number): number {
  const start = progressForChapter(journey, chapter);
  if (journey.chapterAt(start) > chapter + 1e-5) return start;
  let lo = start;
  let hi = 1;
  for (let i = 0; i < 42; i += 1) {
    const mid = (lo + hi) / 2;
    if (journey.chapterAt(mid) <= chapter + 1e-5) lo = mid;
    else hi = mid;
  }
  return lo;
}

/**
 * Build one visual master plus independent audio lanes.
 *
 * Foreground cues remain chronological, but no longer freeze the map: explicit
 * chapter ranges move through their authored beat, a cue on a story dwell walks
 * through the entire camera/animation window, and every other cue advances at
 * normal travel pace. Bed cues overlap the foreground instead of blocking the
 * voyage — the long opening track can play in full while chapters keep moving.
 */
export function buildEpicJourneyTimeline(
  journey: Journey,
  cues: EpicAudioCue[],
  travelBudgetMs: number,
  crossfadeMs: number,
): EpicJourneyTimeline {
  const active = cues
    .filter((cue): cue is EpicAudioCue & { chapter: number } => cue.enabled && cue.chapter !== null)
    .toSorted((a, b) => a.chapter - b.chapter || a.order - b.order);
  const foreground = active.filter((cue) => cue.lane !== "bed");
  const bedsByChapter = new Map<number, EpicAudioCue[]>();
  for (const cue of active) {
    if (cue.lane !== "bed") continue;
    const atChapter = bedsByChapter.get(cue.chapter) ?? [];
    atChapter.push(cue);
    bedsByChapter.set(cue.chapter, atChapter);
  }

  const groups: { chapter: number; cues: EpicAudioCue[] }[] = [];
  for (const cue of foreground) {
    const current = groups.at(-1);
    if (current?.chapter === cue.chapter) current.cues.push(cue);
    else groups.push({ chapter: cue.chapter, cues: [cue] });
  }

  const visual: EpicVisualSegment[] = [];
  const audio: EpicAudioSegment[] = [];
  const scheduledBeds = new Set<string>();
  let cursorProgress = 0;
  let cursorMs = 0;

  const pushVisual = (durationMs: number, fromProgress: number, toProgress: number) => {
    if (durationMs <= 0) return;
    visual.push({
      t0: cursorMs,
      t1: cursorMs + durationMs,
      fromProgress: clamp01(fromProgress),
      toProgress: clamp01(toProgress),
    });
    cursorMs += durationMs;
  };

  const scheduleBeds = (chapter: number) => {
    let leadMs = 0;
    for (const cue of bedsByChapter.get(chapter) ?? []) {
      audio.push({ t0: cursorMs, t1: cursorMs + cue.durationMs, cue });
      scheduledBeds.add(cue.id);
      leadMs = Math.max(leadMs, cue.leadMs);
    }
    return leadMs;
  };

  for (let groupIndex = 0; groupIndex < groups.length; groupIndex += 1) {
    const group = groups[groupIndex];
    const anchor = Math.max(cursorProgress, progressForChapter(journey, group.chapter));
    if (anchor > cursorProgress) {
      pushVisual((anchor - cursorProgress) * travelBudgetMs, cursorProgress, anchor);
      cursorProgress = anchor;
    }

    const groupStartMs = cursorMs;
    let trackStartMs = groupStartMs;
    let trackEndMs = groupStartMs;
    for (let cueIndex = 0; cueIndex < group.cues.length; cueIndex += 1) {
      const cue = group.cues[cueIndex];
      if (cueIndex > 0) trackStartMs = Math.max(groupStartMs, trackEndMs - crossfadeMs);
      trackEndMs = trackStartMs + cue.durationMs;
      audio.push({ t0: trackStartMs, t1: trackEndMs, cue });
    }

    const nextChapter = groups[groupIndex + 1]?.chapter;
    const nextAnchor = nextChapter == null ? 1 : progressForChapter(journey, nextChapter);
    const explicitChapterEnd = Math.max(
      group.chapter,
      ...group.cues.map((cue) => cue.chapterEnd ?? group.chapter),
    );
    const explicitEnd = explicitChapterEnd > group.chapter
      ? progressForChapter(journey, explicitChapterEnd)
      : anchor;
    const heldEnd = progressAfterChapter(journey, group.chapter);
    const audioSpanMs = Math.max(1, trackEndMs - groupStartMs);

    let targetProgress: number;
    let visualDurationMs = audioSpanMs;
    if (explicitEnd > anchor + 1e-6) {
      targetProgress = explicitEnd;
    } else if (heldEnd > anchor + 1e-6) {
      targetProgress = heldEnd;
      // Preserve the journey shot's authored time as well as the complete
      // supplied audio. This is what lets the eight-second Mihawk scene finish.
      visualDurationMs = Math.max(visualDurationMs, (heldEnd - anchor) * travelBudgetMs);
    } else {
      targetProgress = Math.min(nextAnchor, anchor + audioSpanMs / travelBudgetMs);
    }

    pushVisual(visualDurationMs, anchor, targetProgress);
    cursorProgress = targetProgress;

    // A bed begins only after foreground dialogue at the same chapter. Its
    // lead protects the spoken opening before the next foreground cue enters,
    // while the visual master remains free to move.
    const leadMs = scheduleBeds(group.chapter);
    if (leadMs > 0) {
      const leadTarget = Math.min(nextAnchor, cursorProgress + leadMs / travelBudgetMs);
      pushVisual(leadMs, cursorProgress, leadTarget);
      cursorProgress = leadTarget;
    }
  }

  if (cursorProgress < 1) {
    pushVisual((1 - cursorProgress) * travelBudgetMs, cursorProgress, 1);
    cursorProgress = 1;
  }

  // A future bed may be anchored at a chapter with no foreground cue. Place it
  // at the instant the visual master reaches that chapter.
  for (const cue of active) {
    if (cue.lane !== "bed" || scheduledBeds.has(cue.id)) continue;
    const target = progressForChapter(journey, cue.chapter);
    const segment = visual.find((candidate) => target >= candidate.fromProgress && target <= candidate.toProgress);
    const width = segment ? Math.max(1e-9, segment.toProgress - segment.fromProgress) : 1;
    const u = segment ? clamp01((target - segment.fromProgress) / width) : 1;
    const t0 = segment ? segment.t0 + (segment.t1 - segment.t0) * u : cursorMs;
    audio.push({ t0, t1: t0 + cue.durationMs, cue });
  }

  const audioEndMs = audio.reduce((latest, segment) => Math.max(latest, segment.t1), 0);
  if (audioEndMs > cursorMs) pushVisual(audioEndMs - cursorMs, 1, 1);
  const durationMs = Math.max(1, cursorMs);
  audio.sort((a, b) => a.t0 - b.t0 || a.cue.order - b.cue.order);

  const sampleAt = (elapsedMs: number): EpicJourneySample => {
    const elapsed = Math.max(0, Math.min(durationMs, elapsedMs));
    const segment = visual.find((candidate) => elapsed <= candidate.t1) ?? visual.at(-1);
    const width = segment ? Math.max(1, segment.t1 - segment.t0) : 1;
    const u = segment ? clamp01((elapsed - segment.t0) / width) : 1;
    const progress = segment
      ? segment.fromProgress + (segment.toProgress - segment.fromProgress) * u
      : 1;
    const playbacks = audio
      .filter((candidate) => elapsed >= candidate.t0 && elapsed < candidate.t1)
      .map((candidate) => ({ cue: candidate.cue, cueElapsedMs: elapsed - candidate.t0 }));
    const primary = [...playbacks].reverse().find((playback) => playback.cue.lane !== "bed")
      ?? playbacks.at(-1)
      ?? null;
    return {
      progress,
      cue: primary?.cue ?? null,
      cueElapsedMs: primary?.cueElapsedMs ?? 0,
      audio: playbacks,
      done: elapsedMs >= durationMs,
    };
  };

  return { durationMs, sampleAt, cueCount: active.length };
}
