/**
 * components/sim-fx.ts — the small FX registry for 2.5D story simulations.
 *
 * The contract authors 21 event types; the handoff's instruction is a REGISTRY,
 * not a bespoke class per scene: "It is acceptable for the first proof to map
 * unsupported event types to a generic pulse, provided the event remains
 * deterministic and the fallback is logged during development."
 *
 * So: FIVE primitives (arc sweep, radial pulse, particle field, debris burst,
 * flash quad), and a table mapping every authored type onto one of them with a
 * colour and a behaviour knob. Every primitive draws purely as a function of
 * (event, age) — no clocks, no Math.random. Scatter comes from a tiny seeded
 * LCG keyed on the event's authored time, so a rain field at age 1200ms is the
 * same rain field on every machine and every scrub. That is what lets backward
 * scrub replay a fight identically.
 *
 * Pure module: takes a `three` namespace (the layer already paid for the
 * dynamic import) and a parent group. Knows nothing about maps or chapters.
 */

import type * as THREE from "three";
import { streakDisplacementAtAge, type SimFxEvent } from "@/lib/simulation";

type Three = typeof THREE;

export type FxInstance = {
  /** age in ms since the event fired; the instance hides itself past duration. */
  update(ageMs: number): void;
  dispose(): void;
};

type FxKind = "arc" | "pulse" | "particles" | "burst" | "streaks" | "flash";

type FxSpec = {
  kind: FxKind;
  color: number;
  /** particles only: per-type motion. */
  motion?: "rise" | "fall" | "drift" | "hang";
  /** arc only: sweep direction in degrees at age 0. */
  tilt?: number;
  /** scale multiplier on the primitive's footprint. */
  size?: number;
};

/** Every type the East Blue contract authors, mapped onto a primitive.
 * Colours are scene-language: steel for sword arcs, void-purple for Yoru,
 * warm gold for the story pulses, storm tones for Loguetown. */
const FX_TABLE: Record<string, FxSpec> = {
  "slash": { kind: "arc", color: 0xe8f1ff, tilt: -20 },
  "black-blade-slash": { kind: "arc", color: 0x2a1a3a, tilt: -35, size: 1.5 },
  "rubber-stretch": { kind: "arc", color: 0xffd7a0, tilt: 5, size: 1.2 },
  "sand-blade": { kind: "arc", color: 0xd9b46f, tilt: -12, size: 1.5 },
  "kick-trail": { kind: "arc", color: 0xc9e8ff, tilt: -18, size: 1.25 },
  "ballet-spin": { kind: "arc", color: 0xff9fd4, tilt: -30, size: 1.35 },
  "spike-thrust": { kind: "streaks", color: 0xd9e4ed, size: 1.15 },
  "tornado": { kind: "particles", color: 0xd7f0ff, motion: "rise", size: 2.2 },
  "impact": { kind: "pulse", color: 0xfff3c8 },
  "weather-heat": { kind: "pulse", color: 0xffa23d, size: 0.8 },
  "weather-cool": { kind: "pulse", color: 0x83d8ff, size: 0.8 },
  "dehydration-pulse": { kind: "pulse", color: 0xc7a26c, size: 1.2 },
  "blood-counter-impact": { kind: "pulse", color: 0xa85f4c, size: 1.2 },
  "victory-pulse": { kind: "pulse", color: 0xffdd70, size: 1.6 },
  "promise-pulse": { kind: "pulse", color: 0xf5c76a, size: 1.4 },
  "farewell-pulse": { kind: "pulse", color: 0xf5c76a, size: 1.4 },
  "era-pulse": { kind: "pulse", color: 0xffe28a, size: 2.0 },
  "route-pulse": { kind: "pulse", color: 0x8ad1ff, size: 2.0 },
  "crowd": { kind: "pulse", color: 0xc9b28a, size: 1.8 },
  "smoke": { kind: "particles", color: 0x9aa4ad, motion: "rise" },
  "sand-body-disperse": { kind: "particles", color: 0xc99b58, motion: "drift", size: 1.5 },
  "sandstorm": { kind: "particles", color: 0xb98545, motion: "drift", size: 2.3 },
  "moisture-drain": { kind: "particles", color: 0xd8c293, motion: "hang", size: 1.7 },
  "water-drop": { kind: "particles", color: 0x7bd2ff, motion: "fall", size: 0.7 },
  "dust": { kind: "particles", color: 0xcbb491, motion: "hang" },
  "walk-up-dust": { kind: "particles", color: 0xcbb491, motion: "hang" },
  "rain": { kind: "particles", color: 0x9fc4de, motion: "fall", size: 1.6 },
  "wind": { kind: "particles", color: 0xd8e6ee, motion: "drift", size: 1.5 },
  "explosion": { kind: "burst", color: 0xffa14e },
  "armor-break": { kind: "burst", color: 0xd9dde3 },
  "scaffold-break": { kind: "burst", color: 0xa8875f, size: 1.4 },
  "structure-collapse": { kind: "burst", color: 0xa8875f, size: 2.2 },
  "steel-sparks": { kind: "burst", color: 0xd9edff, size: 0.85 },
  "water-splash": { kind: "burst", color: 0x70cfff, size: 1.0 },
  "wet-sand-impact": { kind: "burst", color: 0x8bcbea, size: 1.25 },
  "detach": { kind: "streaks", color: 0xd7b8ff },
  "speed-lines": { kind: "streaks", color: 0xe8f1ff, size: 1.5 },
  "water-spray": { kind: "streaks", color: 0x74d4ff, size: 1.35 },
  "gum-gum-storm": { kind: "streaks", color: 0xf0d5aa, size: 2.3 },
  "enel-lightning": { kind: "flash", color: 0x55cfff, size: 2.3 },
  "rubber-immunity-pulse": { kind: "pulse", color: 0xffef7a, size: 1.5 },
  "gold-ball-weight": { kind: "pulse", color: 0xffcf45, size: 1.35 },
  "thunder-field": { kind: "particles", color: 0x70d8ff, motion: "rise", size: 2.2 },
  "golden-rifle": { kind: "arc", color: 0xffd44f, tilt: -12, size: 2.2 },
  "golden-bell-impact": { kind: "pulse", color: 0xffd65a, size: 2.8 },
  "gear-second-steam": { kind: "particles", color: 0xffd8e5, motion: "rise", size: 1.5 },
  "jet-strike": { kind: "streaks", color: 0xf3d3aa, size: 1.8 },
  "door-door-ripple": { kind: "pulse", color: 0x83e4ff, size: 1.5 },
  "air-door-ambush": { kind: "flash", color: 0xb4f2ff, size: 1.1 },
  "iron-body-impact": { kind: "pulse", color: 0xc6e0ec, size: 1.15 },
  "jet-bazooka-impact": { kind: "burst", color: 0xffdfb5, size: 2.1 },
  "wolf-fang-rush": { kind: "streaks", color: 0xe8edf0, size: 1.5 },
  "kick-impact": { kind: "burst", color: 0xffe7c4, size: 1.1 },
  "claw-slash": { kind: "arc", color: 0xe5ecf1, tilt: -28, size: 1.4 },
  "diable-jambe-ignite": { kind: "particles", color: 0xff6b1f, motion: "rise", size: 1.6 },
  "flambage-impact": { kind: "burst", color: 0xff5a16, size: 2.35 },
  "giraffe-transformation": { kind: "pulse", color: 0xe8bd54, size: 1.25 },
  "four-sword-rush": { kind: "arc", color: 0xe3f3ff, tilt: -38, size: 1.7 },
  "sword-clash": { kind: "burst", color: 0xf1f8ff, size: 1.35 },
  "asura-aura": { kind: "particles", color: 0x7f36db, motion: "rise", size: 2.0 },
  "nine-sword-impact": { kind: "arc", color: 0x8e4deb, tilt: -46, size: 2.6 },
  "finger-pistol-flash": { kind: "flash", color: 0xf4fbff, size: 0.7 },
  "tempest-kick": { kind: "arc", color: 0xd9f4ff, tilt: -34, size: 1.8 },
  "gear-third-impact": { kind: "burst", color: 0xf2c99f, size: 2.2 },
  "rokuogan-shockwave": { kind: "pulse", color: 0xdff6ff, size: 2.4 },
  "jet-gatling": { kind: "streaks", color: 0xf0cfa7, size: 3.0 },
  "defeat-impact": { kind: "burst", color: 0xffe4bd, size: 1.8 },
  "wave": { kind: "pulse", color: 0x6fb3d8, size: 2.0 },
  "lightning": { kind: "flash", color: 0xfffbe6 },
  "clone-flash": { kind: "flash", color: 0xffb2dc, size: 1.25 },
  "poison-flash": { kind: "flash", color: 0xb866e8, size: 1.1 },
  "quicksand": { kind: "pulse", color: 0xb98545, size: 1.8 },
  "hana-hana-bloom": { kind: "particles", color: 0xc58aff, motion: "rise", size: 1.25 },
  "fire-wall": { kind: "arc", color: 0xff7a2f, tilt: 0, size: 2.0 },
  "fire-fist-wave": { kind: "arc", color: 0xff6a1f, tilt: 0, size: 3.0 },
  "smoke-fire-clash": { kind: "pulse", color: 0xffa45d, size: 1.8 },
  "fire-burst": { kind: "burst", color: 0xff6a24, size: 1.5 },
};

/** Deterministic scatter. Same seed → same field, which is the whole point. */
function lcg(seed: number): () => number {
  let s = (seed * 2654435761) >>> 0 || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

const easeOut = (u: number) => 1 - (1 - u) * (1 - u);

/**
 * Build the visual for one fired event, parented under `parent` (the layer's
 * stage group, so metres and billboarding are inherited). `span` is the stage
 * half-width in metres — every footprint scales from it so a 33km stage and a
 * tuned-down one read identically.
 */
export function createFxInstance(
  three: Three,
  parent: THREE.Group,
  event: SimFxEvent,
  span: number,
): FxInstance {
  let spec = FX_TABLE[event.type];
  if (!spec) {
    // The sanctioned fallback — deterministic, and loud in dev.
    if (process.env.NODE_ENV !== "production") {
      console.warn(`sim-fx: unknown FX type "${event.type}" — falling back to generic pulse`);
    }
    spec = { kind: "pulse", color: 0xffffff };
  }
  const size = (spec.size ?? 1) * event.intensity * span;
  const group = new three.Group();
  parent.add(group);

  const materials: THREE.Material[] = [];
  const geometries: THREE.BufferGeometry[] = [];
  const mat = (opts: THREE.MeshBasicMaterialParameters) => {
    const m = new three.MeshBasicMaterial({
      transparent: true,
      depthWrite: false,
      side: three.DoubleSide,
      blending: three.AdditiveBlending,
      ...opts,
    });
    materials.push(m);
    return m;
  };

  let update: (ageMs: number) => void;
  const rand = lcg(event.t + 7);

  switch (spec.kind) {
    case "arc": {
      // A thin sweeping blade-arc: a stretched plane that rotates through the
      // strike and fades. Reads as the classic manga slash streak at map scale.
      const geo = new three.PlaneGeometry(1.6 * size, 0.08 * size);
      geometries.push(geo);
      const m = mat({ color: spec.color });
      const mesh = new three.Mesh(geo, m);
      mesh.position.y = 0.45 * size;
      mesh.rotation.z = ((spec.tilt ?? 0) * Math.PI) / 180;
      group.add(mesh);
      update = (age) => {
        const u = Math.min(1, age / event.duration_ms);
        mesh.rotation.z = (((spec.tilt ?? 0) - 70 * easeOut(u)) * Math.PI) / 180;
        m.opacity = (1 - u) * event.intensity;
        const s = 0.7 + 0.5 * easeOut(u);
        mesh.scale.set(s, s, 1);
      };
      break;
    }
    case "pulse": {
      // Expanding ring on the ground plane — impact, story beat, crowd murmur.
      const geo = new three.RingGeometry(0.42 * size, 0.5 * size, 48);
      geometries.push(geo);
      const m = mat({ color: spec.color });
      const mesh = new three.Mesh(geo, m);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = 0.02 * size;
      group.add(mesh);
      update = (age) => {
        const u = Math.min(1, age / event.duration_ms);
        const s = 0.2 + 1.6 * easeOut(u);
        mesh.scale.set(s, s, 1);
        m.opacity = (1 - u) * event.intensity;
      };
      break;
    }
    case "particles":
    case "burst": {
      // One Points cloud, two motion laws. Particles loop softly over the
      // event window (rain keeps raining); a burst is one-shot outward.
      const n = spec.kind === "burst" ? 48 : 64;
      const origins = new Float32Array(n * 3);
      const vel: [number, number, number][] = [];
      for (let i = 0; i < n; i++) {
        origins[i * 3] = (rand() - 0.5) * 1.6 * size;
        origins[i * 3 + 1] = spec.motion === "fall" ? (0.8 + rand() * 0.8) * size : rand() * 0.25 * size;
        origins[i * 3 + 2] = (rand() - 0.5) * 0.4 * size;
        if (spec.kind === "burst") {
          const a = rand() * Math.PI * 2;
          const up = 0.5 + rand() * 0.9;
          vel.push([Math.cos(a) * (0.4 + rand() * 0.8), up, Math.sin(a) * 0.3]);
        } else {
          vel.push(
            spec.motion === "rise" ? [(rand() - 0.5) * 0.2, 0.5 + rand() * 0.4, 0]
            : spec.motion === "fall" ? [(rand() - 0.5) * 0.1, -(1.2 + rand() * 0.6), 0]
            : spec.motion === "drift" ? [0.8 + rand() * 0.7, (rand() - 0.5) * 0.15, 0]
            : [(rand() - 0.5) * 0.35, 0.1 + rand() * 0.2, 0], // hang
          );
        }
      }
      const geo = new three.BufferGeometry();
      geo.setAttribute("position", new three.BufferAttribute(origins.slice(), 3));
      geometries.push(geo);
      const m = new three.PointsMaterial({
        color: spec.color,
        // PIXELS, not world units: sizeAttenuation divides by view-space z,
        // and under the map's custom projection matrix that z is not what
        // three expects — attenuated points ballooned into a screen-filling
        // white blob (measured, not theorized: the vows scene vanished
        // inside one). Fixed pixel size is projection-proof.
        size: 3,
        transparent: true,
        depthWrite: false,
        blending: three.AdditiveBlending,
        sizeAttenuation: false,
      });
      materials.push(m);
      const points = new three.Points(geo, m);
      group.add(points);
      const pos = geo.getAttribute("position") as THREE.BufferAttribute;
      update = (age) => {
        const u = Math.min(1, age / event.duration_ms);
        // Bursts travel on age; ambient fields loop so rain never runs out
        // mid-window. Both are pure functions of age — scrub-safe.
        const tSec = spec.kind === "burst" ? (age / 1000) : ((age % 1400) / 1000);
        const g = spec.kind === "burst" ? 0.9 : 0;
        for (let i = 0; i < n; i++) {
          const [vx, vy, vz] = vel[i];
          pos.setXYZ(
            i,
            origins[i * 3] + vx * tSec * size,
            Math.max(0, origins[i * 3 + 1] + (vy * tSec - g * tSec * tSec) * size),
            origins[i * 3 + 2] + vz * tSec * size,
          );
        }
        pos.needsUpdate = true;
        m.opacity = (spec.kind === "burst" ? 1 - u : Math.min(1, 4 * u) * (1 - u * 0.6)) * event.intensity;
      };
      break;
    }
    case "streaks": {
      // Horizontal motion streaks — Kuro's speed, Buggy's detached parts.
      const streaks: Array<{ mesh: THREE.Mesh; originX: number; direction: 1 | -1 }> = [];
      for (let i = 0; i < 5; i++) {
        const geo = new three.PlaneGeometry((0.5 + rand() * 0.7) * size, 0.03 * size);
        geometries.push(geo);
        const m = mat({ color: spec.color });
        const mesh = new three.Mesh(geo, m);
        const originX = (rand() - 0.5) * 1.2 * size;
        const direction = i % 2 === 0 ? 1 : -1;
        mesh.position.set(originX, (0.15 + rand() * 0.5) * size, 0);
        group.add(mesh);
        streaks.push({ mesh, originX, direction });
      }
      update = (age) => {
        const u = Math.min(1, age / event.duration_ms);
        for (let i = 0; i < streaks.length; i++) {
          const { mesh, originX, direction } = streaks[i];
          mesh.position.x = originX + streakDisplacementAtAge(age, event.duration_ms, size, direction);
          (mesh.material as THREE.MeshBasicMaterial).opacity = Math.sin(Math.PI * u) * event.intensity;
        }
      };
      break;
    }
    case "flash": {
      // Lightning: a vertical column that blinks hard and dies — the Loguetown
      // scaffold moment. Two quads crossed so it reads from any bearing.
      const column: THREE.Mesh[] = [];
      for (const rotY of [0, Math.PI / 2]) {
        const geo = new three.PlaneGeometry(0.14 * size, 2.4 * size);
        geometries.push(geo);
        const m = mat({ color: spec.color });
        const mesh = new three.Mesh(geo, m);
        mesh.position.y = 1.2 * size;
        mesh.rotation.y = rotY;
        group.add(mesh);
        column.push(mesh);
      }
      update = (age) => {
        const u = Math.min(1, age / event.duration_ms);
        // Deterministic strobe: on-off from the age itself, not a random.
        const strobe = age % 220 < 140 ? 1 : 0.25;
        for (const mesh of column) {
          (mesh.material as THREE.MeshBasicMaterial).opacity = (1 - u) * strobe * event.intensity;
        }
      };
      break;
    }
  }

  return {
    update(ageMs: number) {
      group.visible = ageMs < event.duration_ms;
      if (group.visible) update(ageMs);
    },
    dispose() {
      parent.remove(group);
      for (const g of geometries) g.dispose();
      for (const m of materials) m.dispose();
    },
  };
}
