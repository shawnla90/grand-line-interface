import registry from "@/data/epic-audio-cues.json";

export type EpicAudioCueKind = "voice" | "music" | "sfx";
export type EpicAudioLane = "foreground" | "bed";
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
  lane: EpicAudioLane;
  /** Bed-only headroom before the next foreground cue enters. */
  leadMs: number;
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
    lane: ("lane" in cue ? cue.lane : "foreground") as EpicAudioLane,
    leadMs: "lead_ms" in cue && typeof cue.lead_ms === "number" ? cue.lead_ms : 0,
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
export const EPIC_CROSSFADE_MS = registry.cue_crossfade_ms;
export const EPIC_AUDIO_RIGHTS_STATUS = registry.rights_status;

/**
 * Whether the Epic Journey may be OFFERED to this build's readers. The whole
 * registry carries one rights_status; while it is local_prototype_only the ♫
 * entry point exists in dev only — a production build folds this literal to
 * false and the button (and any path to fetching the tracks) strips out.
 * Flipping the registry to "cleared" (with receipts) is what ships epic audio;
 * there is deliberately no env override.
 */
export const EPIC_AUDIO_SHIPPABLE =
  EPIC_AUDIO_RIGHTS_STATUS === "cleared" || process.env.NODE_ENV !== "production";
