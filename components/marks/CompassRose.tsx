/**
 * components/marks/CompassRose.tsx — an original nautical compass rose.
 *
 * Drawn from primitives in the same house style as the Jolly Rogers: parchment
 * and gold on ink, no imported art. Pure decoration — it sells "sea chart" in a
 * corner of the map. Non-interactive; the map owns all pointer events.
 */

const GOLD = "#e3b04b";
const GOLD_LIT = "#f0c877";
const PARCH = "#efe6d4";
const INK = "#0b1424";

export default function CompassRose({ size = 74 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      aria-hidden="true"
      style={{ opacity: 0.5, filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.6))" }}
    >
      <circle cx="50" cy="50" r="46" fill="none" stroke={GOLD} strokeWidth="0.8" opacity="0.7" />
      <circle cx="50" cy="50" r="40" fill="none" stroke={PARCH} strokeWidth="0.5" opacity="0.4" />
      {/* 32-point tick ring */}
      {Array.from({ length: 32 }).map((_, i) => {
        const a = (i * Math.PI) / 16;
        const r0 = i % 8 === 0 ? 34 : i % 2 === 0 ? 37 : 39;
        const x1 = 50 + r0 * Math.sin(a);
        const y1 = 50 - r0 * Math.cos(a);
        const x2 = 50 + 40 * Math.sin(a);
        const y2 = 50 - 40 * Math.cos(a);
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={PARCH} strokeWidth="0.5" opacity="0.55" />;
      })}
      {/* Intercardinal star (X) */}
      <path d="M50 50 L67 33 L52 48 Z" fill={PARCH} opacity="0.35" />
      <path d="M50 50 L33 33 L48 48 Z" fill={PARCH} opacity="0.25" />
      <path d="M50 50 L67 67 L52 52 Z" fill={PARCH} opacity="0.35" />
      <path d="M50 50 L33 67 L48 52 Z" fill={PARCH} opacity="0.25" />
      {/* Cardinal star — N points up, gold */}
      <path d="M50 12 L54 50 L50 50 Z" fill={GOLD_LIT} />
      <path d="M50 12 L46 50 L50 50 Z" fill={GOLD} />
      <path d="M88 50 L50 54 L50 50 Z" fill={PARCH} opacity="0.6" />
      <path d="M88 50 L50 46 L50 50 Z" fill={PARCH} opacity="0.4" />
      <path d="M50 88 L54 50 L50 50 Z" fill={PARCH} opacity="0.6" />
      <path d="M50 88 L46 50 L50 50 Z" fill={PARCH} opacity="0.4" />
      <path d="M12 50 L50 54 L50 50 Z" fill={PARCH} opacity="0.6" />
      <path d="M12 50 L50 46 L50 50 Z" fill={PARCH} opacity="0.4" />
      <circle cx="50" cy="50" r="2.4" fill={INK} stroke={GOLD} strokeWidth="0.8" />
      <text x="50" y="9" textAnchor="middle" fill={GOLD_LIT} fontSize="7" fontFamily="var(--font-geist-mono), monospace" letterSpacing="0.5">N</text>
    </svg>
  );
}
