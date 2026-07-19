#!/usr/bin/env python3
"""Build the standalone Punk Hazard climate geography runtime package.

The island is a static post-duel geography. Two GLB clips provide only neutral
ambient motion and an explicitly labeled historical FX reconstruction; neither
clip moves or rewinds the island and neither contains character proxies.

Run with Blender 4.5+:
  Blender --background --python scripts/punk-hazard-build.py -- \
    --resolution-x 1400 --resolution-y 1000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_runtime_scene_batch as rt  # noqa: E402


ASSET_ID = "punk-hazard-geographic-system"
CONTRACT = ROOT / f"contracts/{ASSET_ID}.visual.json"
RESEARCH = ROOT / "research/punk-hazard-geography-evidence.json"
SOURCE = ROOT / f"source/{ASSET_ID}.blend"
RUNTIME = ROOT / f"runtime/{ASSET_ID}.glb"
SIDECAR = ROOT / f"runtime/{ASSET_ID}.model.json"
FALLBACK = ROOT / f"renders/runtime/{ASSET_ID}.png"
PREVIEWS = ROOT / "previews"
MANIFEST = ROOT / "manifests/punk-hazard-runtime.json"


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-x", type=int, default=1400)
    parser.add_argument("--resolution-y", type=int, default=1000)
    return parser.parse_args(argv)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> list[int]:
    data = path.read_bytes()[:26]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError(f"Invalid PNG: {path}")
    return list(struct.unpack(">II", data[16:24]))


def gate(obj: bpy.types.Object, component: str, reveal: int, verification: str = "verified",
         *, default_hidden: bool | None = None, active_through: float | None = None) -> bpy.types.Object:
    # Ordinary chapter gates are not permanently hidden: reveal_chapter owns
    # their visibility. Only verified finite windows use default_hidden=true.
    hidden = False if default_hidden is None else default_hidden
    rt.tag(obj, component, reveal, confidence=verification, default_hidden=hidden)
    if active_through is not None:
        obj["active_through_chapter"] = active_through
    return obj


def action(obj: bpy.types.Object, name: str, samples: list[dict]) -> float:
    base_location = obj.location.copy()
    base_rotation = obj.rotation_euler.copy()
    base_scale = obj.scale.copy()
    for sample in samples:
        frame = int(sample["frame"])
        if "location" in sample:
            obj.location = sample["location"]
            obj.keyframe_insert(data_path="location", frame=frame)
        if "rotation" in sample:
            obj.rotation_euler = sample["rotation"]
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        if "scale" in sample:
            obj.scale = sample["scale"]
            obj.keyframe_insert(data_path="scale", frame=frame)
    value = obj.animation_data.action if obj.animation_data else None
    if value is None:
        raise RuntimeError(f"No Blender action created for {name}")
    value.name = name
    for fcurve in value.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "BEZIER"
    obj.location = base_location
    obj.rotation_euler = base_rotation
    obj.scale = base_scale
    obj[f"clip:{name}"] = "ambient" if name.endswith("environment_cycle") else "referenced_historical_reconstruction"
    return (max(sample["frame"] for sample in samples) - min(sample["frame"] for sample in samples)) / 24.0


def parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world


def build_scene(contract: dict, rx: int, ry: int) -> tuple[dict, list[dict]]:
    rt.reset()
    c = rt.collections()
    bpy.context.scene.render.fps = 24
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 120

    ocean = rt.material("M_PH_Outer_Sea", "062638", .22, metallic=.08,
                        emission="0a3f58", emission_strength=.25)
    rock = rt.material("M_PH_Rock_Rim", "3f3d3b", .9)
    hot_rock = rt.material("M_PH_Burning_Rock", "762b18", .76,
                           emission="8e2f18", emission_strength=.32)
    scorched = rt.material("M_PH_Scorched", "3d1711", .9,
                           emission="5d1b10", emission_strength=.16)
    lava = rt.material("M_PH_Lava", "e34316", .28, emission="ff641f", emission_strength=1.8)
    flame = rt.material("M_PH_Flame", "d53c18", .24, emission="ff6a22", emission_strength=2.1, alpha=.82)
    smoke = rt.material("M_PH_Volcanic_Smoke", "3a2b2b", .7,
                        emission="7a3427", emission_strength=.12, alpha=.42)
    cold_rock = rt.material("M_PH_Cold_Rock", "2c7294", .72,
                            emission="327f9f", emission_strength=.24)
    snow = rt.material("M_PH_Snow", "ccecf3", .5,
                       emission="a5dbe8", emission_strength=.32)
    ice = rt.material("M_PH_Ice", "49a6c7", .3, metallic=.08,
                      emission="63d5eb", emission_strength=.72, alpha=.88)
    cold_fog = rt.material("M_PH_Cold_Fog", "a5ddeb", .42,
                           emission="8fd6e7", emission_strength=.4, alpha=.26)
    deep_water = rt.material("M_PH_Crater_Water", "08778c", .18, metallic=.1,
                             emission="18a8bd", emission_strength=.58)
    current = rt.material("M_PH_Current", "82dce7", .22,
                          emission="6ee4f1", emission_strength=1.15, alpha=.76)
    metal = rt.material("M_PH_Industrial", "687177", .46, metallic=.45)
    dark_metal = rt.material("M_PH_Industrial_Dark", "30373c", .52, metallic=.38)
    hazard = rt.material("M_PH_Hazard", "d4a63f", .44, metallic=.12, emission="d89f24", emission_strength=.18)
    steam = rt.material("M_PH_Steam", "b8d7dc", .34, emission="b6edf2", emission_strength=.35, alpha=.34)

    # Outer stage and a dark island rim are visible at first arrival without
    # disclosing the later cold-side treatment.
    gate(rt.island("Punk Hazard outer sea", (0, 0, -.9), 14.4, .45, ocean, c.topology,
                   (1.16, .82), 64), "punk-hazard", 655)
    gate(rt.island("Punk Hazard rock rim", (0, 0, -.05), 9.2, 1.05, rock, c.topology,
                   (1.08, .78), 64), "punk-hazard", 655)

    # Burning Lands: the arrival-side geography seen in chapter 655.
    gate(rt.island("Burning Lands shelf", (-3.45, -2.05, .5), 6.2, .72, hot_rock,
                   c.topology, (1.0, .72), 48), "burning-lands", 655)
    for i in range(21):
        angle = math.tau * i / 21
        radius = 2.2 + (i % 5) * .62
        x = -3.7 + math.cos(angle) * radius
        y = -2.2 + math.sin(angle) * radius * .62
        gate(rt.cone(f"Burning ridge {i+1:02d}", (x, y, 1.05), .55+(i%3)*.16, .05,
                     1.0+(i%4)*.28, scorched, c.landmarks, vertices=11), "burning-lands", 655)
    gate(rt.cone("Burning Lands volcano", (-5.4, -3.0, 3.2), 2.15, .52, 5.4,
                 scorched, c.landmarks, vertices=32), "burning-lands-volcano", 655, "cited_summary")
    gate(rt.torus("Volcano lava caldera", (-5.4, -3.0, 5.82), .58, .16, lava,
                  c.atmosphere), "burning-lands-volcano", 655, "cited_summary")
    for i, points in enumerate((
        [(-5.4,-3.0,5.75),(-4.9,-3.1,4.4),(-4.2,-3.7,2.3),(-3.7,-4.2,1.2)],
        [(-5.5,-2.9,5.7),(-6.0,-2.5,4.0),(-6.3,-1.8,2.0)],
        [(-5.3,-3.1,5.7),(-5.1,-3.9,3.8),(-4.8,-4.8,1.25)],
    )):
        gate(rt.curve(f"Lava run {i+1}", points, .14, lava, c.atmosphere),
             "burning-lands-volcano", 655, "cited_summary")
    fissures = (
        [(-5.0,-3.0,1.03),(-4.0,-2.8,1.05),(-2.8,-2.4,1.04),(-1.5,-2.0,1.02)],
        [(-4.8,-3.5,1.04),(-3.9,-3.7,1.03),(-2.7,-3.45,1.04),(-1.6,-3.8,1.02)],
        [(-4.2,-1.9,1.03),(-3.4,-1.2,1.05),(-2.25,-1.1,1.04),(-1.2,-.65,1.02)],
        [(-3.5,-4.6,1.03),(-2.9,-4.0,1.04),(-2.1,-4.3,1.04),(-1.25,-4.75,1.02)],
        [(-3.6,-2.45,1.06),(-2.9,-2.0,1.07),(-2.2,-2.2,1.06),(-1.55,-1.7,1.03)],
        [(-5.3,-1.5,1.03),(-4.4,-.8,1.05),(-3.4,-.5,1.04),(-2.4,-.2,1.02)],
        [(-5.7,-3.9,1.03),(-5.0,-4.7,1.04),(-4.1,-5.1,1.03),(-3.2,-5.3,1.02)],
    )
    for i, points in enumerate(fissures):
        gate(rt.curve(f"Emissive lava fissure {i+1}", points, .10+(i%2)*.025, lava, c.atmosphere),
             "burning-lands-volcano",655,"derived_visualization")
    for i,(x,y,r) in enumerate(((-3.55,-2.65,.56),(-2.15,-3.15,.43),(-4.2,-1.1,.38))):
        gate(rt.cylinder(f"Lava pool {i+1}",(x,y,1.0),r,.10,lava,c.atmosphere,28,
                         scale_xy=(1.35,.72)),"burning-lands-volcano",655,"derived_visualization")
    for i in range(7):
        gate(rt.sphere(f"Volcanic smoke {i+1}",(-5.35+(i%3)*.22,-3.0+(i%2)*.26,6.15+i*.38),
                       (.55+i*.08,.42+i*.06,.48+i*.08),smoke,c.atmosphere,12,7),
             "burning-lands-volcano",655,"derived_visualization")
    for i in range(15):
        a = math.pi * (.58 + i / 18)
        x = -4.4 + math.cos(a) * (7.0 + (i%3)*.35)
        y = -2.7 + math.sin(a) * 4.5
        gate(rt.sphere(f"Fiery sea plume {i+1:02d}", (x,y,.35+(i%3)*.2),
                       (.48,.34,.7+(i%4)*.12), flame, c.atmosphere, 10, 6), "fiery-sea", 655)

    # Melted former base, warning gate, fence, and deformed street masses.
    base_x, base_y = -1.2, -4.25
    for i in range(13):
        x = base_x - 2.1 + (i % 5) * .9
        y = base_y - .8 + (i // 5) * .95
        obj = rt.cube(f"Melted base shell {i+1:02d}", (x,y,.95+(i%3)*.15),
                      (.34,.28,.65+(i%4)*.12), dark_metal, c.landmarks)
        obj.rotation_euler = (0.0, (i%4-.5)*.08, (i%5-2)*.11)
        gate(obj, "melted-government-base", 655, "cited_summary")
    for side in (-1, 1):
        gate(rt.cube(f"Hazard gate post {side:+}", (base_x+side*1.25,base_y-1.4,1.1),
                     (.16,.18,1.1), hazard, c.landmarks), "melted-government-base", 655, "cited_summary")
    gate(rt.cube("Hazard gate lintel", (base_x,base_y-1.4,2.05),(1.45,.18,.16),
                 hazard,c.landmarks), "melted-government-base", 655, "cited_summary")
    for i in range(8):
        gate(rt.cube(f"Boundary fence {i+1:02d}", (-4.6+i*.95,-6.25,.75),
                     (.42,.05,.72), metal, c.landmarks), "melted-government-base", 655, "cited_summary")

    # Ice Lands and central hydrology become visible with the two-sided discovery.
    gate(rt.island("Ice Lands shelf", (3.55, 2.15, .55), 6.25, .74, cold_rock,
                   c.topology, (1.0,.72), 48), "ice-lands", 657, "verified_summary")
    for i in range(23):
        angle = math.tau * i / 23
        radius = 2.15 + (i%6)*.66
        x = 3.6 + math.cos(angle)*radius
        y = 2.2 + math.sin(angle)*radius*.62
        h = 1.25+(i%5)*.42
        gate(rt.cone(f"Ice mountain {i+1:02d}", (x,y,1.0+h*.48),
                     .72+(i%4)*.16,.06,h,snow,c.landmarks,vertices=10),
             "ice-lands",657,"verified_summary")
    for i,points in enumerate((
        [(1.1,1.0,1.05),(2.0,1.6,1.07),(3.0,1.55,1.06),(4.1,2.0,1.05)],
        [(1.6,2.4,1.05),(2.5,2.1,1.07),(3.5,2.65,1.06),(4.6,2.45,1.05)],
        [(2.0,3.4,1.05),(3.0,3.0,1.07),(4.0,3.5,1.06),(5.0,3.15,1.05)],
        [(2.4,.1,1.05),(3.3,.55,1.07),(4.1,.25,1.06),(5.0,.65,1.05)],
    )):
        gate(rt.curve(f"Glacier face seam {i+1}",points,.095,ice,c.atmosphere),
             "ice-lands",657,"derived_visualization")
    for i in range(8):
        a=math.tau*i/8
        gate(rt.sphere(f"Cold fog bank {i+1:02d}",(3.7+math.cos(a)*4.2,2.0+math.sin(a)*2.8,1.55+(i%3)*.35),
                       (1.0,.62,.38),cold_fog,c.atmosphere,12,7),
             "ice-lands",657,"derived_visualization")
    gate(rt.cylinder("Central crater lake", (0,0,.93), 2.45,.18,deep_water,c.topology,56,
                     scale_xy=(1.0,.82)), "central-crater-lake",657,"verified_summary")
    gate(rt.torus("Central crater luminous rim",(0,0,1.06),2.36,.11,current,c.atmosphere),
         "central-crater-lake",657,"derived_visualization")
    for i in range(10):
        a=math.tau*i/10
        gate(rt.curve(f"Crater current {i+1}",[(math.cos(a)*.4,math.sin(a)*.3,1.05),
                      (math.cos(a)*1.35,math.sin(a)*1.05,1.07),
                      (math.cos(a+.25)*2.05,math.sin(a+.25)*1.62,1.07)],.045,current,c.atmosphere),
             "central-crater-lake",657,"cited_summary")
    gate(rt.curve("Crater sea channel", [(1.1,-1.3,1.03),(2.4,-3.0,.95),(3.4,-5.2,.72),(4.2,-8.0,.2)],
                  .62,deep_water,c.topology), "sea-channel",657,"cited_summary")

    # Ice-side river, natural harbor, captured ships, and iceberg choke.
    gate(rt.curve("Ice Lands river", [(1.55,.55,1.03),(2.8,.25,1.05),(4.1,-.15,1.03),(5.35,-.45,1.0)],
                  .48,deep_water,c.topology), "ice-river",658,"cited_summary")
    gate(rt.curve("Ice river luminous current",[(1.55,.55,1.11),(2.8,.25,1.12),(4.1,-.15,1.11),(5.35,-.45,1.1)],
                  .11,current,c.atmosphere),"ice-river",658,"derived_visualization")
    gate(rt.cylinder("Captured ships harbor", (5.65,-.5,1.0), 1.7,.17,deep_water,c.topology,40,
                     scale_xy=(1.2,.78)), "captured-ships-harbor",658,"cited_summary")
    gate(rt.torus("Captured harbor ice rim",(5.65,-.5,1.1),1.55,.09,ice,c.atmosphere),
         "captured-ships-harbor",658,"derived_visualization")
    for i in range(4):
        x=5.0+(i%2)*1.1; y=-.9+(i//2)*.72
        hull=rt.cube(f"Captured ship hull {i+1}",(x,y,1.28),(.42,.16,.13),dark_metal,c.landmarks)
        hull.rotation_euler[2]=.35+(i%2)*.65
        gate(hull,"captured-ships-harbor",658,"cited_summary")
        gate(rt.beam(f"Captured ship mast {i+1}",(x,y,1.3),(x,y,2.05),.055,metal,c.landmarks),
             "captured-ships-harbor",658,"cited_summary")
    for i,(x,y,s) in enumerate(((2.2,.45,.62),(2.7,.16,.52),(3.25,.02,.68),(4.5,-.28,.48),(5.65,-.12,.72))):
        gate(rt.cone(f"Iceberg choke {i+1}",(x,y,1.25+s*.5),s,.05,1.1+s,ice,c.atmosphere,vertices=8),
             "iceberg-choke",658,"cited_summary")

    # Surviving Third Research Institute embedded at the mountain base.
    lab_x, lab_y = 6.0, 3.55
    gate(rt.cone("Institute mountain",(lab_x,lab_y,3.45),3.0,.4,5.2,cold_rock,c.landmarks,vertices=28),
         "third-research-institute",657,"cited_summary")
    for i,(dx,dy,w,d,h) in enumerate(((-1.1,-1.2,1.15,.72,.82),(0,-1.35,1.35,.82,1.0),(1.2,-1.1,1.0,.68,.76),(-.55,-.35,.82,.65,.72),(.55,-.3,.82,.65,.72))):
        gate(rt.cube(f"Third Institute section {i+1}",(lab_x+dx,lab_y+dy,1.0+h),
                     (w,d,h),metal,c.landmarks), "third-research-institute",657,"cited_summary")
    gate(rt.cube("Third Institute PH-006 facade",(lab_x,lab_y-2.22,2.12),(1.55,.12,.42),
                 hazard,c.landmarks),"laboratory-industrial-system",658,"cited_summary")
    for i in range(6):
        x=lab_x-1.55+(i%3)*1.45; y=lab_y-1.0+(i//3)*.72
        gate(rt.cylinder(f"Laboratory tank {i+1}",(x,y,2.8),.28,.95,dark_metal,c.landmarks,14),
             "laboratory-industrial-system",658,"cited_summary")
        gate(rt.cylinder(f"Laboratory chimney {i+1}",(x+.3,y+.18,3.45),.09,1.25,metal,c.landmarks,10),
             "laboratory-industrial-system",658,"cited_summary")
    for i in range(4):
        gate(rt.curve(f"Laboratory pipe {i+1}",[(lab_x-1.8+i*1.15,lab_y-1.6,1.6),
                      (lab_x-1.8+i*1.15,lab_y-.8,2.1),(lab_x-.5+i*.35,lab_y-.4,2.1)],
                      .08,hazard,c.landmarks), "laboratory-industrial-system",658,"cited_summary")

    # Earlier institutes remain hidden until their destruction is explained.
    for i in range(10):
        x=5.0+(i%5)*.72; y=6.3+(i//5)*.65
        obj=rt.cube(f"Destroyed institute ruin {i+1}",(x,y,1.25+(i%3)*.12),
                    (.3,.26,.48+(i%4)*.12),dark_metal,c.states)
        obj.rotation_euler=(0,(i%3)*.17,(i-4)*.09)
        gate(obj,"first-second-institute-ruins",664,"verified_summary")

    # Neutral ambient clip: one hierarchy breathes/rotates without moving land.
    ambient = gate(rt.torus("Climate boundary ambient root",(0,0,1.42),2.7,.09,current,c.atmosphere),
                   "climate-boundary-ambient",657,"derived_visualization")
    for i in range(9):
        a=math.tau*i/9
        puff=gate(rt.sphere(f"Boundary steam {i+1:02d}",(math.cos(a)*2.35,math.sin(a)*1.8,1.6+(i%3)*.32),
                            (.38,.28,.52),steam,c.atmosphere,10,6),
                  "climate-boundary-ambient",657,"derived_visualization")
        parent_keep_world(puff,ambient)
    ambient_seconds = action(ambient,"punk_hazard_environment_cycle",[
        {"frame":1,"rotation":(0,0,0),"scale":(1,1,1)},
        {"frame":31,"rotation":(0,0,math.pi/2),"scale":(1.08,.96,1.05)},
        {"frame":61,"rotation":(0,0,math.pi),"scale":(.96,1.08,.96)},
        {"frame":91,"rotation":(0,0,math.pi*1.5),"scale":(1.05,1.0,1.08)},
        {"frame":121,"rotation":(0,0,math.tau),"scale":(1,1,1)},
    ])

    # One-shot chapter-658 memory FX. The final island remains unchanged; a
    # joined magma/ice environmental wave expands above it. No actor proxies.
    hot_wave=rt.torus("Historical magma wave",(-2.7,-1.8,1.55),1.0,.18,lava,c.states)
    cold_wave=rt.torus("Historical ice wave",(2.7,1.8,1.57),1.0,.18,ice,c.states)
    bpy.ops.object.select_all(action="DESELECT")
    hot_wave.select_set(True); cold_wave.select_set(True); bpy.context.view_layer.objects.active=hot_wave
    bpy.ops.object.join()
    memory=hot_wave
    memory.name="Duel memory environmental waves"
    gate(memory,"duel-memory-fx",658,"verified_state_window",
         default_hidden=True,active_through=658.999)
    memory["classification"] = "referenced_historical_reconstruction"
    memory["historical_reference_only"] = True
    memory["geography_transform"] = False
    memory_seconds=action(memory,"punk_hazard_duel_memory_fx",[
        {"frame":1,"location":(0,0,1.55),"rotation":(0,0,-.18),"scale":(.12,.12,.12)},
        {"frame":14,"location":(0,0,1.7),"rotation":(0,0,-.08),"scale":(.55,.55,.38)},
        {"frame":38,"location":(0,0,2.0),"rotation":(0,0,.05),"scale":(1.28,1.28,.7)},
        {"frame":68,"location":(0,0,2.3),"rotation":(0,0,.16),"scale":(2.35,2.35,.9)},
        {"frame":96,"location":(0,0,2.55),"rotation":(0,0,.24),"scale":(.12,.12,.12)},
    ])

    bpy.context.scene["historical_state_policy"] = "static post-duel geography; no actor reenactment"
    bpy.context.scene["ambient_clip"] = "punk_hazard_environment_cycle"
    bpy.context.scene["memory_clip"] = "punk_hazard_duel_memory_fx"
    # The fallback cannot evaluate node gates, so author it at the chapter-655
    # arrival state even though ordinary later nodes are runtime-addressable
    # with default_hidden=false.
    for obj in bpy.context.scene.objects:
        reveal=obj.get("reveal_chapter")
        if reveal is not None and int(reveal)>655:
            obj.hide_render=True
    result=rt.finish(ASSET_ID,contract,c,rx,ry,(21,-27,20),(0,0,1.3),
                     safe_full_chapter=664,
                     layout_status="verified_fire_ice_lake_river_harbor_system_interpolated_dimensions")
    result["named_clips"]=["punk_hazard_environment_cycle","punk_hazard_duel_memory_fx"]
    clips=[
        {"name":"punk_hazard_environment_cycle","duration_seconds":round(ambient_seconds,4),
         "mode":"loop","classification":"neutral_ambient","reveal_chapter":657},
        {"name":"punk_hazard_duel_memory_fx","duration_seconds":round(memory_seconds,4),
         "mode":"one_shot","classification":"referenced_historical_reconstruction",
         "reveal_chapter":658,"active_through_chapter":658.999},
    ]
    return result,clips


def set_chapter_visibility(chapter: int, include_memory: bool = False) -> None:
    for obj in bpy.context.scene.objects:
        if not obj.get("component_id"):
            continue
        reveal=obj.get("reveal_chapter")
        active=obj.get("active_through_chapter")
        visible=(reveal is None or int(reveal)<=chapter) and (active is None or chapter<=float(active))
        if obj.get("component_id")=="duel-memory-fx" and not include_memory:
            visible=False
        obj.hide_render=not visible


def render_previews(rx: int, ry: int) -> list[Path]:
    PREVIEWS.mkdir(parents=True,exist_ok=True)
    states=[
        (655,False,1,"ch655-arrival"),
        (657,False,46,"ch657-split"),
        (658,True,52,"ch658-memory-fx"),
        (664,False,92,"ch664-full-geography"),
        (664,False,92,"geographic-system-hero-ch664"),
    ]
    outputs=[]
    scene=bpy.context.scene
    scene.render.resolution_x=rx; scene.render.resolution_y=ry
    for chapter,memory,frame,label in states:
        set_chapter_visibility(chapter,memory)
        scene.frame_set(frame)
        path=PREVIEWS/f"punk-hazard-{label}.png"
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        outputs.append(path)
    # Pillow belongs to the workspace Python rather than Blender's bundled
    # runtime, so invoke it only for the non-authoritative review composite.
    contact=PREVIEWS/"punk-hazard-geographic-system-contact-sheet.png"
    code=(
        "from PIL import Image,ImageDraw; import sys; "
        "paths=sys.argv[1:5]; labels=['CH 655 ARRIVAL','CH 657 FIRE / ICE SPLIT','CH 658 HISTORICAL FX','CH 664 FULL GEOGRAPHY']; "
        "imgs=[Image.open(p).convert('RGBA').resize((700,500)) for p in paths]; "
        "out=Image.new('RGBA',(1400,1000),(7,13,22,255)); d=ImageDraw.Draw(out); "
        "[(out.alpha_composite(im,((i%2)*700,(i//2)*500)),d.rectangle(((i%2)*700,(i//2)*500,(i%2)*700+270,(i//2)*500+30),fill=(0,0,0,190)),d.text(((i%2)*700+10,(i//2)*500+8),labels[i],fill=(255,235,188,255))) for i,im in enumerate(imgs)]; "
        "out.save(sys.argv[-1])"
    )
    subprocess.run(["python3","-c",code,*map(str,outputs),str(contact)],check=True)
    outputs.append(contact)
    return outputs


def glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        magic,version,declared=struct.unpack("<4sII",handle.read(12))
        if magic!=b"glTF" or version!=2 or declared!=path.stat().st_size:
            raise RuntimeError(f"Invalid GLB header: {path}")
        length,chunk_type=struct.unpack("<II",handle.read(8))
        if chunk_type!=0x4E4F534A:
            raise RuntimeError("GLB first chunk is not JSON")
        return json.loads(handle.read(length).decode("utf-8").rstrip(" \t\r\n\x00"))


def export_glb(clips: list[dict]) -> dict:
    # Curves remain editable in the saved .blend; conversion occurs only in
    # this disposable headless process.
    converted=[]
    for obj in list(bpy.context.scene.objects):
        if obj.type!="CURVE":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.hide_viewport=False; obj.hide_set(False); obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        old=obj.name
        bpy.ops.object.convert(target="MESH")
        converted.append(old)
    for obj in bpy.context.scene.objects:
        obj.hide_viewport=False; obj.hide_set(False)
    RUNTIME.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(RUNTIME),export_format="GLB",export_apply=True,
        export_animations=True,export_animation_mode="ACTIONS",
        export_frame_range=True,export_cameras=False,export_lights=False,
        export_extras=True,export_yup=True,export_use_gltfpack=False,
        export_materials="EXPORT",check_existing=False,
    )
    doc=glb_json(RUNTIME)
    actual_clips=[item.get("name") for item in doc.get("animations",[])]
    wanted=[item["name"] for item in clips]
    if set(actual_clips)!=set(wanted):
        raise RuntimeError(f"GLB clips {actual_clips} != {wanted}")
    meshes=[obj for obj in bpy.context.scene.objects if obj.type=="MESH"]
    vertices=sum(len(obj.data.vertices) for obj in meshes)
    triangles=sum(sum(max(1,len(poly.vertices)-2) for poly in obj.data.polygons) for obj in meshes)
    materials={slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}
    minimum=Vector((float("inf"),float("inf"),float("inf")))
    maximum=Vector((float("-inf"),float("-inf"),float("-inf")))
    for obj in meshes:
        for corner in obj.bound_box:
            world=obj.matrix_world @ Vector(corner)
            minimum.x=min(minimum.x,world.x)
            minimum.y=min(minimum.y,world.y)
            minimum.z=min(minimum.z,world.z)
            maximum.x=max(maximum.x,world.x)
            maximum.y=max(maximum.y,world.y)
            maximum.z=max(maximum.z,world.z)
    sidecar={
        "schema_version":1,"id":ASSET_ID,"source_blend":str(SOURCE),"runtime_glb":str(RUNTIME),
        "model_units":"normalized stylized local theatre; app integration owns globe scale",
        "coordinate_system":"glTF 2.0 Y-up converted from Blender Z-up",
        "export":{"exporter":"Blender built-in glTF 2.0 exporter","animations":True,
                  "animation_mode":"ACTIONS","named_clips":clips,"curves_converted_to_mesh":converted,
                  "historical_state_policy":"static post-duel geography; memory clip is environmental FX only"},
        "stats":{"objects":len(meshes),"vertices_input":vertices,"triangles_input":triangles,
                 "materials":len(materials),
                 "bounds_blender":{"min":[round(v,6) for v in minimum],
                                   "max":[round(v,6) for v in maximum]},
                 "bytes":RUNTIME.stat().st_size},
        "build":{"blender":bpy.app.version_string,"glb_sha256":sha(RUNTIME),
                 "glb_header":{"magic":"glTF","version":2,"declared_length":RUNTIME.stat().st_size}},
    }
    SIDECAR.write_text(json.dumps(sidecar,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return sidecar


def write_manifest(build: dict, clips: list[dict], previews: list[Path]) -> None:
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    components=contract["identity"]["components"]
    payload={
        "schema_version":1,"id":ASSET_ID,"generator":"scripts/punk-hazard-build.py",
        "definition":"standalone chapter-gated Punk Hazard LOD1 geography; not registered into shared runtime manifests",
        "registration_status":"not_registered_by_this_lane",
        "maturity":"runtime_blockout_v1",
        "files":{
            "contract":str(CONTRACT.relative_to(ROOT)),"research":str(RESEARCH.relative_to(ROOT)),
            "blend":str(SOURCE.relative_to(ROOT)),"glb":str(RUNTIME.relative_to(ROOT)),
            "model":str(SIDECAR.relative_to(ROOT)),"fallback":str(FALLBACK.relative_to(ROOT)),
            "previews":[str(path.relative_to(ROOT)) for path in previews],
        },
        "chapter_beats":{"pre_reveal_through":654,"base_reveal":655,"two_sided_reveal":657,
                         "historical_cause_reveal":658,"compass_orientation":659,
                         "crater_origin_reveal":661,"safe_full_scene":664},
        "component_gates":components,"named_clips":clips,
        "integration":{"anchor":[18.7035,-5.2418],"anchor_confidence":"derived",
                       "projection_support":["mercator_closeup"],
                       "node_gate_policy":"glTF extras: component_id, reveal_chapter, gate_confidence, default_hidden, active_through_chapter",
                       "ambient_policy":"loop environment cycle only while visible from chapter 657; memory FX is one-shot chapter 658 only"},
        "stats":build["stats"],
        "hashes":{"contract_sha256":sha(CONTRACT),"research_sha256":sha(RESEARCH),
                  "blend_sha256":sha(SOURCE),"glb_sha256":sha(RUNTIME),"model_sha256":sha(SIDECAR),
                  "fallback_sha256":sha(FALLBACK),
                  "preview_sha256":{path.name:sha(path) for path in previews}},
        "fallback":{"pixel_size":png_size(FALLBACK),"bytes":FALLBACK.stat().st_size,"alpha":True},
        "unresolved_gates":contract["unresolved"],
    }
    MANIFEST.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main() -> int:
    options=args()
    for path in (SOURCE.parent,RUNTIME.parent,FALLBACK.parent,PREVIEWS,MANIFEST.parent):
        path.mkdir(parents=True,exist_ok=True)
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    result,clips=build_scene(contract,options.resolution_x,options.resolution_y)
    previews=render_previews(options.resolution_x,options.resolution_y)
    build=export_glb(clips)
    write_manifest(build,clips,previews)
    print(f"BLEND={SOURCE}")
    print(f"GLB={RUNTIME} {RUNTIME.stat().st_size} bytes {sha(RUNTIME)}")
    print(f"FALLBACK={FALLBACK} {FALLBACK.stat().st_size} bytes {sha(FALLBACK)}")
    print(f"CLIPS={json.dumps(clips)}")
    print(f"MANIFEST={MANIFEST}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
