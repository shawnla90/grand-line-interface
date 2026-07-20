import type { JourneyScenePlayback } from "@/lib/journey-treatment";

let journeyScene: JourneyScenePlayback | null = null;

/** Ref-like module bridge: Journey writes at rAF speed without React churn. */
export function setJourneySimulationOverride(next: JourneyScenePlayback | null): void {
  journeyScene = next;
}

export function getJourneySimulationOverride(): JourneyScenePlayback | null {
  return journeyScene;
}
