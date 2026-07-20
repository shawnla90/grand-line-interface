import { ImageResponse } from "next/og";
import { BRAND } from "@/config/brand";

export const alt = `${BRAND.name} — a spoiler-safe One Piece atlas`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        position: "relative",
        overflow: "hidden",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "64px 72px",
        color: "#f3e2b7",
        background: "linear-gradient(145deg, #07141d 0%, #102936 58%, #07131b 100%)",
        fontFamily: "serif",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 520,
          height: 520,
          right: -110,
          top: -170,
          display: "flex",
          borderRadius: "50%",
          border: "2px solid rgba(207, 167, 84, 0.28)",
          boxShadow: "0 0 0 48px rgba(207, 167, 84, 0.05), 0 0 0 110px rgba(207, 167, 84, 0.035)",
        }}
      />

      <div style={{ display: "flex", alignItems: "center", gap: 18, color: "#d5ac5c", fontSize: 22, letterSpacing: 5 }}>
        <span>GRAND LINE INTERFACE</span>
        <span style={{ color: "rgba(243, 226, 183, 0.45)" }}>•</span>
        <span style={{ color: "rgba(243, 226, 183, 0.72)", letterSpacing: 2 }}>FREE & OPEN SOURCE</span>
      </div>

      <div style={{ width: 920, display: "flex", flexDirection: "column", gap: 24 }}>
        <div style={{ display: "flex", fontSize: 76, lineHeight: 0.98, letterSpacing: -2 }}>
          The world exactly<br />where you are.
        </div>
        <div style={{ display: "flex", width: 810, color: "rgba(243, 226, 183, 0.76)", fontSize: 31, lineHeight: 1.35 }}>
          Tell it your chapter or episode. It charts what you know—and fogs everything after.
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 22, color: "#d5ac5c", fontSize: 20, letterSpacing: 3 }}>
        <span>CHAPTER</span><span>→</span><span>EPISODE</span><span>→</span><span>JOURNEY</span><span>→</span><span>3D ISLANDS</span>
      </div>
    </div>,
    size,
  );
}
