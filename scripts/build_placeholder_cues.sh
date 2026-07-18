#!/usr/bin/env bash
#
# build_placeholder_cues.sh — the chapter-159 placeholder masters.
#
# Sound design built from two fully-owned sources, no third-party rights:
#   - Kenney "Impact Sounds" 1.0 (CC0) — wood/plank hits as raw layers
#     https://kenney.nl/assets/impact-sounds
#   - ffmpeg-synthesized noise/sine design (original, ours outright)
#
# These are PLACEHOLDER-GRADE hero cues: they prove the full generate →
# prepare → bind → fire pipeline with honestly-cleared audio. When the
# ElevenLabs account's billing clears, regenerate the six ids with
# scripts/generate_simulation_audio.mjs (same ids, briefs in
# assets/audio/simulations/briefs/ace-fire-fist-ch159.json), re-run prepare,
# and the registry rows swap to the generated masters without touching the
# playback manifest.
#
# Usage: bash scripts/build_placeholder_cues.sh <kenney-impact-audio-dir>

set -euo pipefail

KENNEY="${1:?usage: build_placeholder_cues.sh <kenney-impact-audio-dir>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/assets/audio/simulations/masters"
mkdir -p "$OUT"

# 1. fire-charge-01 — rising pink-noise swell + sine riser (synth, 1.8s)
ffmpeg -hide_banner -y \
  -f lavfi -i "anoisesrc=color=pink:d=1.8:r=48000" \
  -f lavfi -i "aevalsrc=0.5*sin(2*PI*(80+70*t)*t):d=1.8:s=48000" \
  -filter_complex "[0:a]highpass=f=100,lowpass=f=900,volume='0.15+0.85*pow(t/1.8,2)':eval=frame[a0];[1:a]volume='0.35*t/1.8':eval=frame[a1];[a0][a1]amix=inputs=2:normalize=0,afade=t=in:d=0.1,afade=t=out:st=1.55:d=0.25[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/fire-charge-01.wav"

# 2. fire-fist-whoosh-01 — broadband whoosh + low rumble (synth, 2.0s)
ffmpeg -hide_banner -y \
  -f lavfi -i "anoisesrc=color=pink:d=2.0:r=48000" \
  -f lavfi -i "aevalsrc=0.6*sin(2*PI*52*t)*sin(PI*t/2.0):d=2.0:s=48000" \
  -filter_complex "[0:a]highpass=f=120,lowpass=f=1600,volume='pow(sin(PI*t/2.0),1.5)':eval=frame[a0];[0:a]highpass=f=1500,lowpass=f=4000,volume='0.3*pow(sin(PI*t/2.0),3)':eval=frame[hiss];[a0][hiss][1:a]amix=inputs=3:normalize=0,afade=t=out:st=1.7:d=0.3[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/fire-fist-whoosh-01.wav"

# 3. heavy-fleet-impact-01 — Kenney wood hit slowed + 55Hz thump + burst (1.6s)
ffmpeg -hide_banner -y \
  -i "$KENNEY/impactWood_heavy_004.ogg" \
  -f lavfi -i "aevalsrc=0.9*exp(-5*t)*sin(2*PI*55*t):d=1.6:s=48000" \
  -f lavfi -i "anoisesrc=color=white:d=0.3:r=48000" \
  -filter_complex "[0:a]asetrate=44100*0.72,aresample=48000,volume=1.2[wood];[2:a]lowpass=f=2500,afade=t=out:st=0.03:d=0.25,volume=0.45[burst];[wood][1:a][burst]amix=inputs=3:normalize=0:duration=longest,apad=whole_dur=1.6[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/heavy-fleet-impact-01.wav"

# 4. timber-collapse-01 — staggered Kenney planks + heavy wood, roomy tail (2.2s)
ffmpeg -hide_banner -y \
  -i "$KENNEY/impactPlank_medium_000.ogg" \
  -i "$KENNEY/impactPlank_medium_002.ogg" \
  -i "$KENNEY/impactWood_heavy_001.ogg" \
  -i "$KENNEY/impactPlank_medium_004.ogg" \
  -i "$KENNEY/impactWood_medium_003.ogg" \
  -filter_complex "[0:a]adelay=0|0[p0];[1:a]adelay=220|220,volume=0.9[p1];[2:a]asetrate=44100*0.85,aresample=48000,adelay=480|480,volume=1.1[p2];[3:a]adelay=820|820,volume=0.8[p3];[4:a]asetrate=44100*0.8,aresample=48000,adelay=1150|1150[p4];[p0][p1][p2][p3][p4]amix=inputs=5:normalize=0:duration=longest,aecho=0.6:0.35:70|130:0.25|0.18,apad=whole_dur=2.2[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/timber-collapse-01.wav"

# 5. fire-crackle-01 — brown-noise fire bed + sputtering crackle (synth, 3.0s)
ffmpeg -hide_banner -y \
  -f lavfi -i "anoisesrc=color=brown:d=3.0:r=48000" \
  -f lavfi -i "anoisesrc=color=white:d=3.0:r=48000" \
  -filter_complex "[0:a]lowpass=f=500,volume=0.7,tremolo=f=7:d=0.35[bed];[1:a]highpass=f=1800,lowpass=f=6000,volume='0.5*gt(random(0),0.82)':eval=frame[crackle];[bed][crackle]amix=inputs=2:normalize=0,afade=t=in:d=0.2,afade=t=out:st=2.6:d=0.4[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/fire-crackle-01.wav"

# 6. debris-splash-01 — main splash + two staggered secondaries (synth, 2.0s)
ffmpeg -hide_banner -y \
  -f lavfi -i "anoisesrc=color=white:d=2.0:r=48000" \
  -filter_complex "[0:a]asplit=3[m][s1][s2];[m]lowpass=f=2800,highpass=f=200,volume='1.0*exp(-4*t)':eval=frame[main];[s1]adelay=550|550,lowpass=f=2200,volume='0.4*exp(-6*max(t-0.55,0))*gte(t,0.55)':eval=frame[sec1];[s2]adelay=950|950,lowpass=f=1800,volume='0.25*exp(-7*max(t-0.95,0))*gte(t,0.95)':eval=frame[sec2];[main][sec1][sec2]amix=inputs=3:normalize=0,afade=t=out:st=1.7:d=0.3[out]" \
  -map "[out]" -ar 48000 -ac 2 "$OUT/debris-splash-01.wav"

echo "6 placeholder masters written to assets/audio/simulations/masters/"
