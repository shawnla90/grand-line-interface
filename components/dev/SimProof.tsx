"use client";

/**
 * components/dev/SimProof.tsx — the sandbox stage for signed 2.5D story packs.
 *
 * A bare MapLibre map (blank style, no canon, no voyage, no WorldMap) that
 * calls the REAL host — syncSimulations, the same single entry point WorldMap
 * will call — with a scrubbable chapter. This is what lets the ch-51 proof run
 * while the camera session holds WorldMap.tsx: everything except the two-line
 * WorldMap call site is exercised here, including gating, mount/unmount,
 * single-active, and backward-scrub reset.
 *
 * Dev-only by route (app/dev/sim-proof gates on NODE_ENV); the `force` flag it
 * passes exists for this file alone.
 */

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { syncSimulations } from "@/components/sim-models";
import { AudioDirector } from "@/lib/audio-director";
import type { StoryPackId } from "@/config/story-simulations";

const BARATIE: [number, number] = [-165, -40];
const WHISKY_PEAK: [number, number] = [-121.3706, 4.162];
const NANOHANA: [number, number] = [-102.8707, 0.4813];
const RAINBASE: [number, number] = [-116.2875, 6.0506];
const ALUBARNA: [number, number] = [-120.1992, -0.7873];
const SKYPIEA: [number, number] = [-91.1362, 17.0745];
const ENIES_LOBBY: [number, number] = [-68.3696, -7.1283];

export default function SimProof({
  initialChapter,
  initialPack,
}: {
  initialChapter: number;
  initialPack: StoryPackId;
}) {
  const div = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [chapter, setChapter] = useState(initialChapter);
  const [pack, setPack] = useState<StoryPackId>(initialPack);
  const [loaded, setLoaded] = useState(false);
  // The harness's audio-unlock gesture: the same director the app uses, so
  // the browser audit exercises real gesture-gated playback (window.__simAudio
  // reports fired cues, voices, and unlock state).
  const [sound, setSound] = useState(false);

  useEffect(() => {
    if (!div.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: div.current,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "bg", type: "background", paint: { "background-color": "#0b1d33" } }],
      },
      center: initialPack === "enies-lobby-saga-2d-v1"
        ? ENIES_LOBBY
        : initialPack === "skypiea-saga-2d-v1"
          ? SKYPIEA
          : initialPack === "arabasta-saga-2d-v1"
            ? (initialChapter >= 158 ? NANOHANA : WHISKY_PEAK)
            : BARATIE,
      zoom: 5.2,
      // The 2.5D cards are VERTICAL billboards ("camera-facing around local
      // up, do not flatten onto the map" — the contract). A pitch-0 top-down
      // camera sees them edge-on, i.e. not at all; the app's close-map views
      // (dive/orbit, journey dwell) are pitched, so the harness matches.
      pitch: 58,
      attributionControl: false,
    });
    mapRef.current = map;
    map.on("load", () => setLoaded(true));
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [initialChapter, initialPack]);

  useEffect(() => {
    if (!loaded || !mapRef.current) return;
    void syncSimulations(mapRef.current, chapter, true, pack);
  }, [loaded, chapter, pack]);

  const jump = (lngLat: [number, number], ch: number, nextPack: StoryPackId = pack) => {
    mapRef.current?.jumpTo({ center: lngLat, zoom: 5.2, pitch: 58 });
    setPack(nextPack);
    setChapter(ch);
  };

  return (
    <div style={{ position: "fixed", inset: 0 }}>
      <div ref={div} style={{ position: "absolute", inset: 0 }} />
      <div
        style={{
          position: "absolute", top: 12, left: 12, padding: "10px 14px",
          background: "rgba(6,14,25,0.88)", color: "#dbe7f3", borderRadius: 8,
          font: "13px/1.5 var(--font-geist-sans, sans-serif)", maxWidth: 340,
        }}
      >
        <strong>sim-proof</strong> · {pack} · chapter{" "}
        <input
          type="number"
          value={chapter}
          min={1}
          max={1200}
          onChange={(e) => setChapter(Number(e.target.value) || 1)}
          style={{ width: 64, background: "#122a44", color: "inherit", border: "1px solid #2b4a6b", borderRadius: 4, padding: "2px 6px" }}
          data-testid="chapter-input"
        />
        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
          <button onClick={() => jump(BARATIE, 49, "east-blue-saga-2d")} data-testid="go-49">Baratie ch49</button>
          <button onClick={() => jump(BARATIE, 51, "east-blue-saga-2d")} data-testid="go-51">duel ch51</button>
          <button onClick={() => jump([-121.15, -39.31], 93, "east-blue-saga-2d")} data-testid="go-93">Arlong ch93</button>
          <button onClick={() => jump([-174, -20], 99, "east-blue-saga-2d")} data-testid="go-99">scaffold ch99</button>
          <button onClick={() => jump([-177, -12], 100, "east-blue-saga-2d")} data-testid="go-100">vows ch100</button>
          <button onClick={() => jump(WHISKY_PEAK, 106, "arabasta-saga-2d-v1")} data-testid="go-106">Whisky ch106</button>
          <button onClick={() => jump(WHISKY_PEAK, 107, "arabasta-saga-2d-v1")} data-testid="go-107">Zoro ch107</button>
          <button onClick={() => jump(WHISKY_PEAK, 114, "arabasta-saga-2d-v1")} data-testid="go-114">Robin ch114</button>
          <button onClick={() => jump(NANOHANA, 158, "arabasta-saga-2d-v1")} data-testid="go-158">Ace ch158</button>
          <button onClick={() => jump(NANOHANA, 159, "arabasta-saga-2d-v1")} data-testid="go-159">Fire Fist ch159</button>
          <button onClick={() => jump(RAINBASE, 176, "arabasta-saga-2d-v1")} data-testid="go-176">Crocodile ch176</button>
          <button onClick={() => jump(ALUBARNA, 187, "arabasta-saga-2d-v1")} data-testid="go-187">Sanji ch187</button>
          <button onClick={() => jump(ALUBARNA, 190, "arabasta-saga-2d-v1")} data-testid="go-190">Nami ch190</button>
          <button onClick={() => jump(ALUBARNA, 194, "arabasta-saga-2d-v1")} data-testid="go-194">Zoro ch194</button>
          <button onClick={() => jump(ALUBARNA, 198, "arabasta-saga-2d-v1")} data-testid="go-198">Aqua Luffy ch198</button>
          <button onClick={() => jump(ALUBARNA, 203, "arabasta-saga-2d-v1")} data-testid="go-203">Crocodile final ch203</button>
          <button onClick={() => jump(SKYPIEA, 278, "skypiea-saga-2d-v1")} data-testid="go-278">Enel pre-gate ch278</button>
          <button onClick={() => jump(SKYPIEA, 279, "skypiea-saga-2d-v1")} data-testid="go-279">Enel ch279</button>
          <button onClick={() => jump(ENIES_LOBBY, 386, "enies-lobby-saga-2d-v1")} data-testid="go-386">Gear Second pre-gate ch386</button>
          <button onClick={() => jump(ENIES_LOBBY, 387, "enies-lobby-saga-2d-v1")} data-testid="go-387">Blueno ch387</button>
          <button onClick={() => jump(ENIES_LOBBY, 414, "enies-lobby-saga-2d-v1")} data-testid="go-414">Diable pre-gate ch414</button>
          <button onClick={() => jump(ENIES_LOBBY, 415, "enies-lobby-saga-2d-v1")} data-testid="go-415">Jabra ch415</button>
          <button onClick={() => jump(ENIES_LOBBY, 416, "enies-lobby-saga-2d-v1")} data-testid="go-416">Kaku ch416</button>
          <button onClick={() => jump(ENIES_LOBBY, 417, "enies-lobby-saga-2d-v1")} data-testid="go-417">Asura ch417</button>
          <button onClick={() => jump(ENIES_LOBBY, 418, "enies-lobby-saga-2d-v1")} data-testid="go-418">Lucci ch418</button>
          <button
            onClick={() => {
              const director = AudioDirector.get();
              const next = !sound;
              if (next) {
                director.unlock();
                director.setMuted(false);
              } else {
                director.setMuted(true);
              }
              setSound(next);
            }}
            data-testid="sound-unlock"
            aria-pressed={sound}
          >
            {sound ? "🔊 sound on" : "🔈 sound"}
          </button>
        </div>
        <div style={{ marginTop: 6, opacity: 0.7 }}>
          the real syncSimulations host on a bare map — window.__simScenes has the clocks
        </div>
      </div>
    </div>
  );
}
