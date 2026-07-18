/**
 * components/entry/PositionChart.tsx — where on the planet this page is.
 *
 * A server-safe inline SVG, drawn from the same model world-geometry.ts states:
 * Grand Line = the equator, Red Line = the 0/180 meridian, Calm Belts at
 * |lat| 9.5..17, the four Blues in the quadrants. That is chapter-1 knowledge —
 * the map draws all of it before any island is charted — so the chart leaks
 * nothing: the only page-specific mark is this island's own dot, and the page
 * already prints the coordinates as text. Fogged pages never reach this
 * component (the route's entry gate decides; this renders).
 *
 * No other island, no route, no presence — orientation, not a second map.
 */

// The map's own palette (components/WorldMap.tsx `C`), inlined because this
// renders on the server where importing the MapLibre module would be waste.
const INK = {
  ocean: "#071324",
  grat: "#16233c",
  gold: "#e3b04b",
  redLine: "#9c4436",
  lane: "#123049",
  beltDeep: "#060f1e",
  label: "#5b6880",
} as const;

/** Grand Line sea-lane half-width / belt bounds, per world-geometry.ts. */
const LANE = 8.7;
const BELT_INNER = 9.5;
const BELT_OUTER = 17;

const SEAS: { name: string; lng: number; lat: number }[] = [
  { name: "North Blue", lng: -90, lat: 48 },
  { name: "West Blue", lng: 90, lat: 48 },
  { name: "East Blue", lng: -90, lat: -48 },
  { name: "South Blue", lng: 90, lat: -48 },
];

const W = 360;
const H = 180;
const x = (lng: number) => ((lng + 180) / 360) * W;
const y = (lat: number) => ((90 - lat) / 180) * H;

export default function PositionChart({
  lng,
  lat,
  name,
}: {
  lng: number;
  lat: number;
  name: string;
}) {
  const px = x(lng);
  const py = y(lat);
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${name} charted at latitude ${lat.toFixed(2)}, longitude ${lng.toFixed(2)}`}
      className="block w-full rounded-sm border border-rope/60"
    >
      <rect width={W} height={H} fill={INK.ocean} />

      {/* Calm Belts — the dead water bracketing the Grand Line. */}
      <rect x={0} y={y(BELT_OUTER)} width={W} height={y(BELT_INNER) - y(BELT_OUTER)} fill={INK.beltDeep} opacity={0.9} />
      <rect x={0} y={y(-BELT_INNER)} width={W} height={y(-BELT_OUTER) - y(-BELT_INNER)} fill={INK.beltDeep} opacity={0.9} />
      {/* The navigable Grand Line channel. */}
      <rect x={0} y={y(LANE)} width={W} height={y(-LANE) - y(LANE)} fill={INK.lane} opacity={0.85} />

      {/* Graticule every 30°. */}
      {[-150, -120, -90, -60, -30, 30, 60, 90, 120, 150].map((g) => (
        <line key={`m${g}`} x1={x(g)} y1={0} x2={x(g)} y2={H} stroke={INK.grat} strokeWidth={0.5} />
      ))}
      {[-60, -30, 30, 60].map((g) => (
        <line key={`p${g}`} x1={0} y1={y(g)} x2={W} y2={y(g)} stroke={INK.grat} strokeWidth={0.5} />
      ))}

      {/* Grand Line: the equator. Red Line: the 0/180 meridian — one great
          circle, so it appears at the centre and both edges of the sheet. */}
      <line x1={0} y1={y(0)} x2={W} y2={y(0)} stroke={INK.gold} strokeWidth={1} opacity={0.55} />
      <line x1={x(0)} y1={0} x2={x(0)} y2={H} stroke={INK.redLine} strokeWidth={2} opacity={0.9} />
      <line x1={0.75} y1={0} x2={0.75} y2={H} stroke={INK.redLine} strokeWidth={1.5} opacity={0.9} />
      <line x1={W - 0.75} y1={0} x2={W - 0.75} y2={H} stroke={INK.redLine} strokeWidth={1.5} opacity={0.9} />

      {SEAS.map((sea) => (
        <text
          key={sea.name}
          x={x(sea.lng)}
          y={y(sea.lat)}
          textAnchor="middle"
          fill={INK.label}
          opacity={0.75}
          style={{ font: "6.5px ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase" }}
        >
          {sea.name}
        </text>
      ))}

      {/* This island. Crosshair ticks first so the dot sits on top. */}
      <line x1={px} y1={0} x2={px} y2={H} stroke={INK.gold} strokeWidth={0.5} opacity={0.28} />
      <line x1={0} y1={py} x2={W} y2={py} stroke={INK.gold} strokeWidth={0.5} opacity={0.28} />
      <circle cx={px} cy={py} r={6.5} fill={INK.gold} opacity={0.18} />
      <circle cx={px} cy={py} r={2.6} fill={INK.gold} />
    </svg>
  );
}
