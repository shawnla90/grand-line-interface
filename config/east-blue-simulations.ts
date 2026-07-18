/**
 * config/east-blue-simulations.ts — the tunable knobs for the East Blue 2.5D
 * story layer. Numbers a human dials in by looking at the map, kept out of the
 * renderer so tuning is a one-file diff (the projection-overrides.ts posture).
 */

/** Build-time flag (inlined by Next). Default OFF is the asset track's hard
 * rule #1; nobody sees a simulation without opting in. */
export const EAST_BLUE_2D_ON = process.env.NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS === "1";

/**
 * The stage's width in metres: actor x = ±1 spans this. MAP-SCALE THEATRE, not
 * a canon measurement — same doctrine as the GLB models' visual_fit, and on
 * this chart the fit is planetary: the atlas paints a fantasy world onto a
 * full 360° globe (the East Blue alone spans ~70° of longitude), so islands
 * are already hundreds of km tall on screen. Measured at the ch51 proof:
 * 33km made Mihawk a 10px speck at zoom 5.2; 600km reads as a story beat
 * (cards ~200px, the sea chart still visible around them).
 */
export const STAGE_SPAN_M = 600_000;

/**
 * Scenes mount at the same zoom the GLB islands cross-fade in
 * (WorldMap's GLB_MIN_ZOOM) — one shared "close enough for the third
 * dimension" threshold instead of two competing ones.
 */
export const SIM_MIN_ZOOM = 4.6;

/** Fade-in ms when a scene mounts; fade-out is the layer removal (instant),
 * because backward scrub must re-fog NOW, not after a courtesy fade. */
export const SIM_FADE_IN_MS = 450;

/* The journey's East Blue moment table used to live here (five hand-typed
 * MomentDefs). It moved into the playback manifest — canon/story_scene_playback.json
 * rows with journey.enabled — where every pack's treatment now lives as data.
 * config/journey-stops.ts builds the moments from the compiled artifact. */
