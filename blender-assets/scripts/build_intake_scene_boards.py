#!/usr/bin/env python3
"""Render original SVG production boards for the priority narrative systems."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from html import escape
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
OUT = ROOT / "sketches/intake"
PREVIEWS = OUT / "previews"


def read(contract_id: str) -> dict:
    return json.loads((CONTRACTS / f"{contract_id}.visual.json").read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shell(title: str, subtitle: str, body: str, badge: str, accent: str = "#f1c86a") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1100" viewBox="0 0 1800 1100">
<title>{escape(title)}</title>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#102a38"/><stop offset="1" stop-color="#050d14"/></linearGradient>
  <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#1b748e"/><stop offset="1" stop-color="#092938"/></linearGradient>
  <linearGradient id="stone" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e0d0b3"/><stop offset="1" stop-color="#745f55"/></linearGradient>
  <linearGradient id="cloud" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fffde8"/><stop offset="1" stop-color="#9ed8e5"/></linearGradient>
  <filter id="glow"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="shadow"><feDropShadow dx="0" dy="10" stdDeviation="10" flood-opacity=".35"/></filter>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#75dfef"/></marker>
</defs>
<rect width="1800" height="1100" fill="url(#bg)"/>
<circle cx="1510" cy="-60" r="390" fill="{accent}" opacity=".06"/>
<text x="64" y="75" fill="#fff7df" font-family="Georgia,serif" font-size="45">{escape(title)}</text>
<text x="66" y="114" fill="#95b8c1" font-family="Arial,sans-serif" font-size="19">{escape(subtitle)}</text>
<rect x="1500" y="46" width="238" height="54" rx="27" fill="#0a1720" stroke="{accent}" stroke-width="2"/>
<text x="1619" y="80" text-anchor="middle" fill="{accent}" font-family="Arial,sans-serif" font-size="17">{escape(badge)}</text>
{body}
</svg>\n'''


def footer(lines: list[str], accent: str = "#f1c86a") -> str:
    output = ['<rect x="60" y="962" width="1680" height="102" rx="18" fill="#07141d" stroke="#315363"/>']
    for index, line in enumerate(lines):
        color = accent if index == 0 else "#b8cdd1"
        size = 16 if index == 0 else 15
        output.append(f'<text x="88" y="{998 + index * 29}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}">{escape(line)}</text>')
    return "\n".join(output)


def loguetown(contract: dict) -> str:
    buildings = []
    for index in range(13):
        x = 75 + index * 128
        height = 165 + (index * 47) % 170
        y = 800 - height
        color = "#283f49" if index % 2 else "#344d56"
        buildings.append(f'<rect x="{x}" y="{y}" width="105" height="{height}" fill="{color}" stroke="#77909a" stroke-width="2"/>')
        buildings.append(f'<path d="M{x - 8} {y}L{x + 52} {y - 48}L{x + 113} {y}Z" fill="#6b3d3c" stroke="#bd7868" stroke-width="3"/>')
        for row in range(3):
            buildings.append(f'<rect x="{x + 18}" y="{y + 30 + row * 48}" width="18" height="25" fill="#e8c276" opacity=".75"/>')
            buildings.append(f'<rect x="{x + 68}" y="{y + 30 + row * 48}" width="18" height="25" fill="#e8c276" opacity=".75"/>')
    people = []
    for index in range(65):
        x = 110 + (index * 83) % 1570
        y = 820 + (index * 29) % 90
        people.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#111820"/><path d="M{x} {y + 5}v17" stroke="#111820" stroke-width="5"/>')
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="#0c202b" stroke="#335865"/>
<circle cx="1350" cy="300" r="112" fill="#e4c77f" opacity=".65"/>
{''.join(buildings)}
<path d="M60 820L1740 820L1600 935L200 935Z" fill="#a79d87"/>
<path d="M120 935L700 770M1680 935L1090 770" stroke="#ded1b5" stroke-width="5" opacity=".45"/>
<g transform="translate(900 390)" filter="url(#shadow)">
  <path d="M-118 420L-82 0H82L118 420" fill="#41362e" stroke="#d3b37a" stroke-width="8"/>
  <path d="M-150 15H150M-135 100H135M-125 190H125M-120 280H120M-118 365H118" stroke="#d3b37a" stroke-width="9"/>
  <path d="M-82 0L82 420M82 0L-82 420" stroke="#b9915f" stroke-width="7"/>
  <rect x="-104" y="-38" width="208" height="54" fill="#63392f" stroke="#e0c08a" stroke-width="5"/>
  <path d="M-145 420H145" stroke="#e0c08a" stroke-width="14"/>
  <text x="0" y="-60" text-anchor="middle" fill="#f4d487" font-family="Georgia,serif" font-size="25">EXECUTION PLATFORM</text>
</g>
{''.join(people)}
<rect x="105" y="192" width="350" height="154" rx="16" fill="#08151c" stroke="#786e5b"/>
<text x="132" y="230" fill="#f1c86a" font-family="Arial,sans-serif" font-size="17">CHAPTER 1 — HISTORICAL STATE</text>
<text x="132" y="267" fill="#e3eaE8" font-family="Georgia,serif" font-size="23">Roger execution tableau</text>
<text x="132" y="301" fill="#9db5bb" font-family="Arial,sans-serif" font-size="16">crowd • wind • scaffold occupancy</text>
<rect x="1345" y="704" width="335" height="154" rx="16" fill="#08151c" stroke="#607c8a"/>
<text x="1372" y="742" fill="#84d7e6" font-family="Arial,sans-serif" font-size="17">LATER — GATED STORM STATE</text>
<text x="1372" y="779" fill="#e3eaE8" font-family="Georgia,serif" font-size="23">Mirrored near-execution</text>
<text x="1372" y="813" fill="#9db5bb" font-family="Arial,sans-serif" font-size="16">rain • lightning • crowd panic</text>
{footer(["BLENDER RULE — one permanent scaffold, three switchable states", "Free roam: empty landmark  •  Chapter 1: Roger history  •  Later verified gate: storm mirror"])}'''
    return shell("LOGUETOWN — THE SCAFFOLD AT THE HEART OF THE CITY", "Event landmark board • city / square / scaffold / repeated cinematic composition", body, "PRIORITY 01")


def dressrosa(contract: dict) -> str:
    houses = []
    for index in range(42):
        angle = math.tau * index / 42
        ring = 200 + (index % 4) * 48
        x = 850 + math.cos(angle) * ring
        y = 560 + math.sin(angle) * ring * .64
        color = ("#e77d63", "#e7bb5f", "#78b89d", "#a987c7")[index % 4]
        houses.append(f'<rect x="{x - 13:.1f}" y="{y - 10:.1f}" width="26" height="20" rx="4" fill="{color}" stroke="#fff0cf" stroke-width="2" transform="rotate({index * 17} {x:.1f} {y:.1f})"/>')
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="url(#sea)" stroke="#335865"/>
<ellipse cx="850" cy="585" rx="525" ry="330" fill="#587f4e" stroke="#d9c48e" stroke-width="13" filter="url(#shadow)"/>
<path d="M630 558L695 430L850 360L1010 430L1085 558L1018 705L850 780L685 705Z" fill="#c27b70" stroke="#ffe2a1" stroke-width="12"/>
<path d="M720 565L755 478L850 438L948 478L983 565L948 650L850 690L755 650Z" fill="#794f65" stroke="#f4c274" stroke-width="8"/>
<path d="M790 456L790 388L830 352L850 305L870 352L910 388L910 456Z" fill="#e3d5b5" stroke="#fff2cd" stroke-width="6"/>
<text x="850" y="584" text-anchor="middle" fill="#fff2cf" font-family="Georgia,serif" font-size="24">KING'S PLATEAU</text>
<text x="850" y="615" text-anchor="middle" fill="#debddd" font-family="Arial,sans-serif" font-size="15">PALACE — PRE-PICA</text>
{''.join(houses)}
<circle cx="435" cy="646" r="78" fill="#d7a653" stroke="#fff0bb" stroke-width="7"/>
<path d="M393 647Q435 590 477 647Q435 705 393 647Z" fill="#a54845"/>
<text x="435" y="756" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="16">CORRIDA COLOSSEUM</text>
<circle cx="1110" cy="705" r="72" fill="#d87196" stroke="#ffe1c3" stroke-width="7"/>
<circle cx="1085" cy="678" r="18" fill="#f6cc5c"/><circle cx="1138" cy="692" r="20" fill="#ef7d75"/><circle cx="1112" cy="729" r="22" fill="#a9d47b"/>
<text x="1110" y="806" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="16">FLOWER HILL</text>
<ellipse cx="1450" cy="375" rx="230" ry="150" fill="#3f8c58" stroke="#bde5a2" stroke-width="11"/>
<path d="M1325 375Q1450 330 1575 375" fill="none" stroke="#788b91" stroke-width="23"/>
<path d="M1325 375Q1450 330 1575 375" fill="none" stroke="#dae4df" stroke-width="7" stroke-dasharray="15 9"/>
<path d="M1210 420Q1120 450 1080 490" fill="none" stroke="#788b91" stroke-width="23"/>
<path d="M1210 420Q1120 450 1080 490" fill="none" stroke="#dae4df" stroke-width="7" stroke-dasharray="15 9"/>
<text x="1450" y="380" text-anchor="middle" fill="#f2ffd9" font-family="Georgia,serif" font-size="25">GREEN BIT</text>
<text x="1307" y="474" fill="#dbe8e5" font-family="Arial,sans-serif" font-size="15">IRON BRIDGE — NORTH CONNECTOR</text>
<rect x="96" y="195" width="370" height="134" rx="17" fill="#07151d" stroke="#6e5366"/>
<text x="123" y="233" fill="#f1c86a" font-family="Arial,sans-serif" font-size="17">DO NOT MERGE THESE IDEAS</text>
<text x="123" y="270" fill="#dbe5e4" font-family="Arial,sans-serif" font-size="17">Bridge → Green Bit</text>
<text x="123" y="300" fill="#dbe5e4" font-family="Arial,sans-serif" font-size="17">Palace → central King's Plateau</text>
<rect x="1325" y="666" width="330" height="170" rx="17" fill="#07151d" stroke="#bd7581"/>
<text x="1352" y="704" fill="#ef9fa9" font-family="Arial,sans-serif" font-size="17">TEMPORAL VARIANT</text>
<text x="1352" y="741" fill="#fff" font-family="Georgia,serif" font-size="22">Pica remodels the city</text>
<text x="1352" y="776" fill="#afc2c7" font-family="Arial,sans-serif" font-size="15">Palace relocates to a new plateau</text>
<text x="1352" y="804" fill="#afc2c7" font-family="Arial,sans-serif" font-size="15">at Flower Hill; gate to verify.</text>
{footer(["BLENDER RULE — two terrain layouts, never one blended impossible city", "Pre-Pica collection  •  Post-Pica collection  •  Birdcage as a temporary event volume"])}'''
    return shell("DRESSROSA + GREEN BIT — RELATIONSHIPS BEFORE DETAIL", "Cited topology board • bearings only where supported • city states remain separate", body, "PRIORITY 01")


def zou(contract: dict) -> str:
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="#082434" stroke="#335865"/>
<rect x="59" y="650" width="1682" height="285" fill="url(#sea)"/>
<path d="M60 650H1740" stroke="#7fe3ef" stroke-width="6"/>
<path d="M60 910Q300 875 540 910T1020 910T1500 910T1740 910V935H60Z" fill="#192b2f" stroke="#536968" stroke-width="5"/>
<g transform="translate(900 0)" filter="url(#shadow)">
  <path d="M-320 410Q-225 265 -40 276Q170 240 335 355Q380 405 337 468Q280 535 135 526L-65 535Q-215 530 -300 470Z" fill="#6a7770" stroke="#c4cfbf" stroke-width="8"/>
  <ellipse cx="315" cy="370" rx="112" ry="94" fill="#6a7770" stroke="#c4cfbf" stroke-width="8"/>
  <path d="M382 395Q510 470 492 620Q478 745 590 777" fill="none" stroke="#6a7770" stroke-width="62" stroke-linecap="round"/>
  <path d="M382 395Q510 470 492 620Q478 745 590 777" fill="none" stroke="#c4cfbf" stroke-width="8" stroke-linecap="round"/>
  <path d="M-195 490Q-240 620 -205 747L-178 910H-102L-105 748Q-76 620 -85 505Z" fill="#596963" stroke="#bac7b8" stroke-width="8"/>
  <path d="M95 506Q62 620 100 744L122 910H202L195 742Q224 615 205 492Z" fill="#596963" stroke="#bac7b8" stroke-width="8"/>
  <path d="M-205 747Q-150 795 -105 748M100 744Q150 790 195 742" fill="none" stroke="#d7e0d1" stroke-width="7"/>
  <path d="M-255 327Q-170 235 -75 300Q18 225 120 302Q195 263 280 330L260 365H-255Z" fill="#668a54" stroke="#bee097" stroke-width="7"/>
  <path d="M-220 320Q-175 280 -130 320M-95 315Q-40 260 10 315M45 315Q100 265 150 315" fill="none" stroke="#8dd275" stroke-width="10"/>
  <g fill="#d2b57e" stroke="#fff0c3" stroke-width="3">
    <rect x="-135" y="282" width="38" height="35"/><rect x="-70" y="270" width="46" height="48"/><rect x="5" y="282" width="35" height="35"/><rect x="72" y="269" width="48" height="49"/>
  </g>
  <text x="0" y="238" text-anchor="middle" fill="#e9ffd8" font-family="Georgia,serif" font-size="26">ZOU / MOKOMO DUKEDOM</text>
  <circle cx="347" cy="345" r="7" fill="#fff8c7"/>
</g>
<path d="M1460 742Q1310 600 1170 525" fill="none" stroke="#a8eff5" stroke-width="18" opacity=".78"/>
<path d="M1460 742Q1310 600 1170 525" fill="none" stroke="#e9ffff" stroke-width="5" stroke-dasharray="10 13"/>
<text x="1395" y="575" fill="#d9ffff" font-family="Arial,sans-serif" font-size="17">ERUPTION RAIN ARC</text>
<path d="M410 655V880" stroke="#8ee6f0" stroke-width="3" stroke-dasharray="12 9" marker-end="url(#arrow)"/>
<text x="150" y="720" fill="#9ec5cf" font-family="Arial,sans-serif" font-size="16">SEA LEVEL</text>
<text x="120" y="900" fill="#9ec5cf" font-family="Arial,sans-serif" font-size="16">SEAFLOOR</text>
<rect x="100" y="208" width="390" height="155" rx="17" fill="#07151d" stroke="#6f8b7e"/>
<text x="127" y="247" fill="#f1c86a" font-family="Arial,sans-serif" font-size="17">RUNTIME BEHAVIOR</text>
<text x="127" y="284" fill="#dfe8e4" font-family="Arial,sans-serif" font-size="18">Zunesha is the moving anchor.</text>
<text x="127" y="316" fill="#a9c0c5" font-family="Arial,sans-serif" font-size="15">The atlas point opens an encounter;</text>
<text x="127" y="342" fill="#a9c0c5" font-family="Arial,sans-serif" font-size="15">it is not a permanent canon location.</text>
{footer(["BLENDER RULE — rig the elephant first; the city rides on the back collection", "Extreme scale LODs: seafloor legs  •  cloud crossing  •  city blockout  •  trunk rain event"])}'''
    return shell("ZOU — A COUNTRY ON A MOVING ELEPHANT", "Vertical scale board • moving entity / carried nation / recurring water event", body, "PRIORITY 01", "#bde39a")


def sabaody(contract: dict) -> str:
    nodes = []
    edges = []
    positions = []
    for index in range(79):
        ring = 0 if index < 18 else 1 if index < 45 else 2
        within = index if ring == 0 else index - 18 if ring == 1 else index - 45
        count = (18, 27, 34)[ring]
        angle = math.tau * within / count + ring * .09
        radius = (190, 310, 430)[ring]
        x = 920 + math.cos(angle) * radius
        y = 535 + math.sin(angle) * radius * .69
        positions.append((x, y))
        color = ("#8ecb8a", "#72b7a4", "#4c948f")[ring]
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="{color}" stroke="#dffff0" stroke-width="2"/><text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" fill="#082029" font-family="Arial,sans-serif" font-size="10">{index + 1}</text>')
        if within:
            px, py = positions[index - 1]
            edges.append(f'<path d="M{px:.1f} {py:.1f}Q{(px + x) / 2:.1f} {(py + y) / 2 - 12:.1f} {x:.1f} {y:.1f}" fill="none" stroke="#9bc3b6" stroke-width="3" opacity=".35"/>')
    bubbles = []
    for index in range(55):
        x = 470 + (index * 137) % 940
        y = 230 + (index * 89) % 570
        r = 7 + (index % 5) * 3
        bubbles.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#b7eff1" fill-opacity=".08" stroke="#d9ffff" stroke-width="2" opacity=".7"/>')
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="#082933" stroke="#335865"/>
<ellipse cx="920" cy="560" rx="520" ry="360" fill="#102d2d" stroke="#416b61" stroke-width="8"/>
<path d="M810 690Q750 555 825 400Q900 260 1000 405Q1075 560 1015 690" fill="#4d4033" stroke="#a48762" stroke-width="32"/>
<path d="M820 675Q720 710 615 780M845 680Q790 760 760 860M980 680Q1060 750 1170 792M1005 665Q1110 685 1275 705" fill="none" stroke="#795f43" stroke-width="28" stroke-linecap="round"/>
{''.join(edges)}
{''.join(nodes)}
{''.join(bubbles)}
<text x="920" y="530" text-anchor="middle" fill="#efffdc" font-family="Georgia,serif" font-size="39">79 GROVES</text>
<text x="920" y="570" text-anchor="middle" fill="#9dd8c5" font-family="Arial,sans-serif" font-size="18">numbered root nodes • bridge graph • bubble ecology</text>
<rect x="95" y="210" width="340" height="172" rx="17" fill="#07151d" stroke="#6c917f"/>
<text x="122" y="248" fill="#f1c86a" font-family="Arial,sans-serif" font-size="17">CURRENT 3D STUDY: DEMOTED</text>
<text x="122" y="286" fill="#dce7e3" font-family="Georgia,serif" font-size="21">3 generic groves ≠ Sabaody</text>
<text x="122" y="322" fill="#a3bcc0" font-family="Arial,sans-serif" font-size="15">Reuse its palette and bubble material.</text>
<text x="122" y="349" fill="#a3bcc0" font-family="Arial,sans-serif" font-size="15">Rebuild topology from this network.</text>
<rect x="1380" y="692" width="285" height="152" rx="17" fill="#07151d" stroke="#7bb9b4"/>
<text x="1407" y="731" fill="#a8eff1" font-family="Arial,sans-serif" font-size="17">BUBBLE LAYER</text>
<text x="1407" y="767" fill="#e3eaea" font-family="Arial,sans-serif" font-size="16">transport • hotels</text>
<text x="1407" y="796" fill="#e3eaea" font-family="Arial,sans-serif" font-size="16">helmets • coating</text>
<text x="1407" y="824" fill="#9bb5ba" font-family="Arial,sans-serif" font-size="14">instanced by LOD and zone</text>
{footer(["BLENDER RULE — build one root/trunk kit, then 79 addressable grove collections", "The numbered node graph is mandatory; exact canonical grove placement remains a research layer."])}'''
    return shell("SABAODY — NOT ISLANDS, A MANGROVE NETWORK", "System correction board • 79 numbered Yarukiman groves / bridges / bubbles / nested landmarks", body, "PRIORITY 01", "#91dfb0")


def skypiea(contract: dict) -> str:
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="#5a9db4" stroke="#96d9e8"/>
<rect x="59" y="760" width="1682" height="174" fill="#073446"/>
<path d="M60 760H1740" stroke="#9cf0f4" stroke-width="7"/>
<path d="M870 935Q795 805 850 672Q915 535 870 430" fill="none" stroke="#c7f6ff" stroke-width="90" opacity=".65"/>
<path d="M870 935Q795 805 850 672Q915 535 870 430" fill="none" stroke="#f7ffff" stroke-width="18" stroke-dasharray="14 18"/>
<g fill="url(#cloud)" stroke="#f7fff6" stroke-width="7" filter="url(#shadow)">
  <path d="M180 565Q250 485 340 540Q405 435 500 530Q590 482 660 565Q580 630 420 627Q260 630 180 565Z"/>
  <path d="M1040 500Q1110 420 1210 478Q1300 370 1420 475Q1510 430 1605 520Q1510 592 1320 585Q1135 592 1040 500Z"/>
  <path d="M730 310Q795 250 870 290Q935 220 1015 295Q1080 266 1142 325Q1060 375 930 370Q800 380 730 310Z"/>
</g>
<text x="420" y="565" text-anchor="middle" fill="#365f66" font-family="Georgia,serif" font-size="25">ANGEL ISLAND</text>
<path d="M1085 500Q1190 420 1395 452Q1510 470 1555 530Q1480 655 1300 670Q1120 650 1055 565Z" fill="#667d45" stroke="#d6c487" stroke-width="10"/>
<path d="M1170 568Q1250 520 1335 565Q1380 600 1435 578" fill="none" stroke="#b98e55" stroke-width="11"/>
<path d="M1288 528Q1210 455 1245 360Q1270 260 1255 184" fill="none" stroke="#788449" stroke-width="38" stroke-linecap="round"/>
<path d="M1288 528Q1210 455 1245 360Q1270 260 1255 184" fill="none" stroke="#d0d889" stroke-width="7"/>
<rect x="1265" y="548" width="95" height="55" fill="#9f7652" stroke="#f1d18a" stroke-width="5"/>
<text x="1310" y="700" text-anchor="middle" fill="#fff5c8" font-family="Georgia,serif" font-size="24">UPPER YARD — SOLID JAYA LAND</text>
<text x="1310" y="731" text-anchor="middle" fill="#d8ebdf" font-family="Arial,sans-serif" font-size="15">SHANDORA RUINS WITHIN</text>
<text x="1180" y="250" fill="#edf3b9" font-family="Arial,sans-serif" font-size="17">GIANT JACK</text>
<g transform="translate(930 305)">
  <rect x="-32" y="-18" width="64" height="54" fill="#d4a849" stroke="#fff0a1" stroke-width="5"/>
  <path d="M-50 -18Q0 -72 50 -18" fill="#e9c75d" stroke="#fff0a1" stroke-width="5"/>
  <circle cx="0" cy="10" r="14" fill="#ffec91"/>
</g>
<text x="930" y="405" text-anchor="middle" fill="#fff1a0" font-family="Arial,sans-serif" font-size="16">GOLDEN BELFRY CLOUD — GATED</text>
<text x="165" y="740" fill="#dbffff" font-family="Arial,sans-serif" font-size="18">WHITE-WHITE SEA / CLOUD OCEAN</text>
<text x="742" y="878" fill="#d9ffff" font-family="Arial,sans-serif" font-size="17">KNOCK-UP STREAM</text>
<path d="M900 445V220" stroke="#efffff" stroke-width="4" stroke-dasharray="11 9" marker-end="url(#arrow)"/>
<rect x="95" y="210" width="390" height="158" rx="17" fill="#164457" stroke="#d9ffff"/>
<text x="122" y="249" fill="#fff0a1" font-family="Arial,sans-serif" font-size="17">THE STREAM IS THE ENTRANCE</text>
<text x="122" y="286" fill="#fff" font-family="Georgia,serif" font-size="22">The destination is a layered world.</text>
<text x="122" y="322" fill="#d0e7eb" font-family="Arial,sans-serif" font-size="15">cloud sea • cloud island • solid land</text>
<text x="122" y="348" fill="#d0e7eb" font-family="Arial,sans-serif" font-size="15">ruins • vine axis • higher bell cloud</text>
{footer(["BLENDER RULE — separate cloud volumes from the solid Upper Yard mesh", "Existing Knock-Up Stream GLB becomes the transition into this scene, not the finished Skypiea asset."])}'''
    return shell("SKYPIEA — BUILD THE WORLD ABOVE THE STREAM", "Vertical destination board • cloud ocean / Angel Island / Upper Yard / Giant Jack / Belfry", body, "PRIORITY 01", "#fff0a1")


def water7(contract: dict) -> str:
    nodes = {
        "water-7": (420, 535, 120, "#63a7b9"),
        "enies-lobby": (1390, 535, 120, "#d8d7c7"),
        "pucci": (760, 300, 64, "#d99872"),
        "st-poplar": (930, 245, 64, "#79b77c"),
        "san-faldo": (1095, 315, 64, "#e4be64"),
        "shift-station": (865, 620, 45, "#9f8d75"),
    }
    lines = []
    for end in ("enies-lobby", "pucci", "st-poplar", "san-faldo"):
        x1, y1, _, _ = nodes["water-7"]
        x2, y2, _, _ = nodes[end]
        cy = min(y1, y2) - 75 if end != "enies-lobby" else y1 + 105
        lines.append(f'<path d="M{x1 + 80} {y1}Q{(x1 + x2) / 2} {cy} {x2 - 70} {y2}" fill="none" stroke="#093a4a" stroke-width="22"/>')
        lines.append(f'<path d="M{x1 + 80} {y1}Q{(x1 + x2) / 2} {cy} {x2 - 70} {y2}" fill="none" stroke="#9ce7e9" stroke-width="5" stroke-dasharray="17 11"/>')
    node_svg = []
    for key, (x, y, r, color) in nodes.items():
        label = key.replace("-", " ").upper()
        node_svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="#ecffff" stroke-width="7" filter="url(#shadow)"/>')
        node_svg.append(f'<text x="{x}" y="{y + 6}" text-anchor="middle" fill="#08222c" font-family="Georgia,serif" font-size="{22 if r > 80 else 14}">{escape(label)}</text>')
    body = f'''
<rect x="58" y="155" width="1684" height="780" rx="24" fill="url(#sea)" stroke="#64b4c7"/>
<path d="M60 720Q260 680 460 720T860 720T1260 720T1660 720T1740 720V935H60Z" fill="#0d5265" opacity=".42"/>
{''.join(lines)}
{''.join(node_svg)}
<g transform="translate(975 585)" filter="url(#shadow)">
  <rect x="-90" y="-32" width="180" height="65" rx="14" fill="#292c2b" stroke="#ebd9a3" stroke-width="5"/>
  <rect x="-38" y="-88" width="82" height="58" fill="#323536" stroke="#ebd9a3" stroke-width="5"/>
  <path d="M-20 -88V-135" stroke="#252728" stroke-width="23"/>
  <circle cx="-52" cy="38" r="22" fill="#7b472d" stroke="#f3ca7c" stroke-width="5"/><circle cx="48" cy="38" r="22" fill="#7b472d" stroke="#f3ca7c" stroke-width="5"/>
  <path d="M-110 30Q-155 50 -190 28M110 30Q155 50 190 28" stroke="#e3ffff" stroke-width="8" opacity=".7"/>
</g>
<text x="975" y="690" text-anchor="middle" fill="#fff1bf" font-family="Georgia,serif" font-size="22">PUFFING TOM — ANIMATED VEHICLE</text>
<path d="M550 775H1330" stroke="#061e28" stroke-width="24" opacity=".75"/>
<path d="M550 775H1330" stroke="#a0e6e8" stroke-width="6" stroke-dasharray="19 12"/>
<text x="940" y="812" text-anchor="middle" fill="#d7ffff" font-family="Arial,sans-serif" font-size="16">RAILS JUST BELOW OCEAN SURFACE • SWAY WITH TIDES</text>
<rect x="98" y="208" width="375" height="155" rx="17" fill="#07151d" stroke="#86d7e5"/>
<text x="125" y="247" fill="#f1c86a" font-family="Arial,sans-serif" font-size="17">CHAPTER 322 — NETWORK REVEAL</text>
<text x="125" y="284" fill="#e8efed" font-family="Georgia,serif" font-size="22">The route appears on the globe.</text>
<text x="125" y="320" fill="#a7c0c5" font-family="Arial,sans-serif" font-size="15">Select a line → train travels → inset opens.</text>
<text x="125" y="347" fill="#a7c0c5" font-family="Arial,sans-serif" font-size="15">Bearings remain schematic until verified.</text>
<rect x="1320" y="720" width="330" height="145" rx="17" fill="#07151d" stroke="#818fa4"/>
<text x="1347" y="758" fill="#a9b9d9" font-family="Arial,sans-serif" font-size="17">AQUA LAGUNA STATE</text>
<text x="1347" y="795" fill="#e6ecec" font-family="Arial,sans-serif" font-size="16">storm volume • Rocketman pursuit</text>
<text x="1347" y="824" fill="#9eb4ba" font-family="Arial,sans-serif" font-size="15">chapter gate still to verify</text>
{footer(["MAPLIBRE + BLENDER RULE — the line is geographic UI; the train, stations, spray, and storm are 3D", "Known network nodes: Water 7 • Enies Lobby • Pucci • St. Poplar • San Faldo • Shift Station"])}'''
    return shell("WATER 7 — THE SEA TRAIN BECOMES A TRAVEL SYSTEM", "Route-network board • chapter-gated rails / stations / animated train / storm state", body, "PRIORITY 01", "#94e5eb")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    jobs: dict[str, Callable[[dict], str]] = {
        "loguetown-roger-execution": loguetown,
        "dressrosa-green-bit": dressrosa,
        "zou-zunesha": zou,
        "sabaody-grove-network": sabaody,
        "skypiea-sky-system": skypiea,
        "water-7-sea-train-network": water7,
    }
    outputs = []
    for contract_id, builder in jobs.items():
        contract = read(contract_id)
        svg_path = OUT / f"{contract_id}.svg"
        png_path = PREVIEWS / f"{contract_id}.png"
        svg_path.write_text(builder(contract), encoding="utf-8")
        subprocess.run(
            ["sips", "-s", "format", "png", str(svg_path), "--out", str(png_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        outputs.append({
            "id": contract_id,
            "contract": f"contracts/{contract_id}.visual.json",
            "contract_sha256": sha(CONTRACTS / f"{contract_id}.visual.json"),
            "sketch": str(svg_path.relative_to(ROOT)),
            "sketch_sha256": sha(svg_path),
            "preview": str(png_path.relative_to(ROOT)),
            "preview_sha256": sha(png_path),
            "status": "system_sketch_not_final_art",
        })
        print(f"wrote {svg_path}")
        print(f"wrote {png_path}")
    manifest_path = OUT / "intake-board-manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "generator": "scripts/build_intake_scene_boards.py",
        "coordinate_policy": "relationship schematics; no atlas coordinate geometry",
        "outputs": outputs,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
