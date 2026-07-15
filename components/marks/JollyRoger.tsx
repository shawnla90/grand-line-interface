/**
 * components/marks/JollyRoger.tsx — the React face of jollyRoger.ts.
 *
 * A thin wrapper so components can drop a crew flag in with <JollyRoger />. The
 * markup comes from jollyRoger.ts (our own static string, no user input), so
 * dangerouslySetInnerHTML is safe here and keeps ONE source of truth for the
 * vector — the ship marker (imperative) and this component draw the same flag.
 */

import { jollyRogerSvg } from "./jolly-roger";

export default function JollyRoger({
  crewSlug,
  size = 28,
  title,
  className,
}: {
  crewSlug: string;
  size?: number;
  /** Accessible label, e.g. the crew name. */
  title?: string;
  className?: string;
}) {
  return (
    <span
      className={className}
      role="img"
      aria-label={title ?? "Jolly Roger"}
      style={{ display: "inline-flex", lineHeight: 0 }}
      dangerouslySetInnerHTML={{ __html: jollyRogerSvg(crewSlug, { size }) }}
    />
  );
}
