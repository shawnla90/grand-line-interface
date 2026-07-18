import registry from "@/data/epic-audio-cues.json";

export type EpicAudioCueKind = "voice" | "music" | "sfx";
export type EpicAudioVerification =
  | "chapter_source"
  | "chapter_title"
  | "character_gate"
  | "conservative_gate"
  | "needs_identification";

export type EpicAudioCue = {
  id: string;
  sourceFile: string;
  src: string;
  kind: EpicAudioCueKind;
  chapter: number | null;
  chapterEnd?: number;
  order: number;
  durationMs: number;
  label: string;
  caption: string;
  gain: number;
  verification: EpicAudioVerification;
  enabled: boolean;
};

type RegistryCue = (typeof registry.cues)[number];

function normalizeCue(cue: RegistryCue): EpicAudioCue {
  return {
    id: cue.id,
    sourceFile: cue.source_file,
    src: cue.src,
    kind: cue.kind as EpicAudioCueKind,
    chapter: cue.chapter,
    ...(cue.chapter_end == null ? {} : { chapterEnd: cue.chapter_end }),
    order: cue.order,
    durationMs: cue.duration_ms,
    label: cue.label,
    caption: cue.caption,
    gain: cue.gain,
    verification: cue.verification as EpicAudioVerification,
    enabled: cue.enabled !== false,
  };
}

/** All supplied tracks, including the disabled human-verification queue. */
export const EPIC_AUDIO_CUES = registry.cues.map(normalizeCue);

/** Only spoiler-gated tracks eligible for the running Epic Journey. */
export const ACTIVE_EPIC_AUDIO_CUES = EPIC_AUDIO_CUES.filter(
  (cue): cue is EpicAudioCue & { chapter: number } => cue.enabled && cue.chapter !== null,
).sort((a, b) => a.chapter - b.chapter || a.order - b.order);

export const EPIC_TRAVEL_BUDGET_MS = registry.travel_budget_ms;
export const EPIC_CUE_GAP_MS = registry.cue_gap_ms;
export const EPIC_AUDIO_RIGHTS_STATUS = registry.rights_status;
