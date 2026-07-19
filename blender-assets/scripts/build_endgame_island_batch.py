#!/usr/bin/env python3
"""Build Egghead, Wano/Onigashima, and Elbaph as local runtime theatres.

These are deliberately stylized LOD1 world models. They encode cited relative
topology and chapter-aware component IDs, not guessed globe measurements.

Run with Blender 4.5+:
  Blender --background --python scripts/build_endgame_island_batch.py -- \
    --resolution-x 1400 --resolution-y 1000
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_runtime_scene_batch as rt  # noqa: E402


ASSETS = (
    "egghead-future-island-system",
    "wano-onigashima-country-system",
    "elbaph-adam-world-system",
)
MANIFEST = ROOT / "manifests/endgame-island-builds.json"


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=ASSETS)
    parser.add_argument("--resolution-x", type=int, default=1400)
    parser.add_argument("--resolution-y", type=int, default=1000)
    return parser.parse_args(argv)


def pagoda(prefix, loc, size, wall, roof, target, component, reveal):
    x, y, z = loc
    for tier in range(3):
        width = size * (1.0 - tier * .18)
        rt.cube(f"{prefix} tier {tier + 1}", (x, y, z + tier * size * .62),
                (width * .58, width * .46, size * .26), wall, target,
                component=component, reveal=reveal)
        top = rt.cone(f"{prefix} roof {tier + 1}",
                      (x, y, z + tier * size * .62 + size * .33),
                      width * .82, width * .55, size * .18, roof, target,
                      vertices=8, component=component, reveal=reveal)
        top.rotation_euler[2] = math.pi / 8


def torii(prefix, loc, size, wood, target, component, reveal):
    x, y, z = loc
    rt.cylinder(f"{prefix} left post", (x - size*.45, y, z + size), size*.09,
                size*2, wood, target, vertices=10, component=component, reveal=reveal)
    rt.cylinder(f"{prefix} right post", (x + size*.45, y, z + size), size*.09,
                size*2, wood, target, vertices=10, component=component, reveal=reveal)
    rt.cube(f"{prefix} upper beam", (x, y, z + size*1.72),
            (size*.72, size*.10, size*.10), wood, target,
            component=component, reveal=reveal)
    rt.cube(f"{prefix} lower beam", (x, y, z + size*1.45),
            (size*.54, size*.08, size*.08), wood, target,
            component=component, reveal=reveal)


def geographic_clip(obj, name, keys):
    """Create a named object-transform action sampled by chapter in the app."""
    base_loc = obj.location.copy()
    base_rot = obj.rotation_euler.copy()
    data = obj.animation_data_create()
    data.action = None
    for key in keys:
        frame = int(key["frame"])
        if "location" in key:
            obj.location = key["location"]
            obj.keyframe_insert(data_path="location", frame=frame)
        if "rotation" in key:
            obj.rotation_euler = key["rotation"]
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    action = data.action
    if action is None:
        raise RuntimeError(f"Blender did not create action {name}")
    action.name = name
    for fcurve in action.fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
    track = data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, int(action.frame_range[0]), action)
    strip.name = name
    data.action = None
    data.use_nla = False
    obj[f"clip:{name}"] = "chapter_sampled_geography"
    obj.location = base_loc
    obj.rotation_euler = base_rot


def build_egghead(contract, rx, ry):
    rt.reset(); c = rt.collections()
    sea = rt.material("M_Egghead_Cold_Sea", "062c52", .2, metallic=.08,
                      emission="0b4775", emission_strength=.3)
    ice = rt.material("M_Egghead_Ice", "a9d9f0", .32, metallic=.05,
                      emission="7bc8ef", emission_strength=.25)
    rock = rt.material("M_Egghead_Rock", "344e61", .82)
    green = rt.material("M_Egghead_Tropical", "4e9b4d", .72)
    road = rt.material("M_Egghead_Road", "253743", .58, metallic=.25)
    white = rt.material("M_Egghead_Porcelain", "e6e0d2", .38, metallic=.08)
    glass = rt.material("M_Egghead_Glass", "4dc7e5", .16, metallic=.3,
                        emission="43d8ff", emission_strength=1.1)
    magenta = rt.material("M_Egghead_Magenta", "9d3f9e", .24, metallic=.4,
                          emission="ee4fd8", emission_strength=2.2)
    cloud = rt.material("M_Egghead_Cloud", "d9eff3", .62,
                        emission="bfe9ff", emission_strength=.25)
    brain = rt.material("M_Egghead_Records", "a96bb1", .5,
                        emission="d58cdb", emission_strength=.35)

    rt.island("Egghead cold-sea stage", (0, 0, -.85), 14.5, .45, sea, c.topology,
              (1.12, .8), 64, component="egghead-winter-sea", reveal=1061)
    for i in range(17):
        a = math.tau*i/17
        r = 10.7 + (i % 3)*1.1
        rt.cone(f"Egghead iceberg {i+1:02d}", (math.cos(a)*r, math.sin(a)*r*.73, -.1),
                .7+(i%4)*.16, .06, 1.5+(i%3)*.45, ice, c.atmosphere,
                vertices=7, component="egghead-winter-sea", reveal=1061)
    rt.island("Egghead natural shelf", (0, 0, -.08), 8.4, 1.2, rock, c.topology,
              (1.0, .76), 56, component="egghead", reveal=1061)
    rt.island("Fabriophase climate lawn", (0, 0, .48), 7.8, .42, green, c.topology,
              (1.0, .74), 56, component="fabriophase", reveal=1061)
    for ring in (3.0, 5.0, 6.6):
        rt.torus(f"Future city route ring {ring}", (0, 0, .82), ring, .07, glass,
                 c.landmarks, component="future-city", reveal=1061)
    for i in range(24):
        a = math.tau*i/24
        ring = 3.2 if i % 2 else 5.2
        x, y = math.cos(a)*ring, math.sin(a)*ring*.72
        h = 1.1 + (i%5)*.32
        rt.cylinder(f"Future tower {i+1:02d}", (x, y, .9+h/2), .28+(i%3)*.06,
                    h, white, c.landmarks, vertices=12,
                    component="future-city", reveal=1061)
        rt.sphere(f"Future dome {i+1:02d}", (x, y, .9+h), (.42, .42, .24), glass,
                  c.landmarks, 12, 7, component="future-city", reveal=1061)
    rt.cylinder("Fabriophase central factory", (0, 0, 2.15), 1.15, 3.1, road,
                c.landmarks, 16, component="central-factory", reveal=1061)
    for a in (0, math.tau/3, math.tau*2/3):
        rt.cone("Factory exhaust stack", (math.cos(a)*.68, math.sin(a)*.68, 4.0),
                .28, .16, 1.2, white, c.landmarks, vertices=12,
                component="central-factory", reveal=1061)
    for i in range(9):
        rt.torus(f"Scrapyard coil {i+1}", (-5.4+(i%3)*.48, -2.8+(i//3)*.48, .95),
                 .16+(i%2)*.05, .05, magenta, c.landmarks,
                 rotation=(math.pi/2, 0, 0), component="scrapyard", reveal=1061)
    for i in range(22):
        a = math.tau*i/22
        rt.sphere(f"Island cloud {i+1:02d}", (math.cos(a)*4.8, math.sin(a)*4.8*.72, 5.1+(i%3)*.12),
                  (1.55, 1.25, .68), cloud, c.atmosphere, 14, 8,
                  component="cloud-plant", reveal=1065)
    rt.island("Labophase cloud platform", (0, 0, 5.05), 4.8, .32, cloud, c.topology,
              (1.0, .78), 48, component="labophase", reveal=1065)
    rt.sphere("Cracked egg laboratory", (0, 0, 8.0), (3.15, 3.15, 3.65), white,
              c.landmarks, 24, 16, component="labophase", reveal=1065)
    for z, mat in ((7.0, glass), (7.55, magenta), (8.1, glass)):
        rt.torus(f"Frontier Dome band {z}", (0, 0, z), 3.18, .10, mat, c.landmarks,
                 component="frontier-dome", reveal=1065)
    for i, (x, y, comp) in enumerate(((-2.4, .3, "lab-building-a"),
                                      (2.2, .5, "lab-building-b"),
                                      (0, -2.2, "lab-building-c"))):
        rt.cylinder(f"Upper lab {i+1}", (x, y, 5.95), .58, 1.5, road,
                    c.landmarks, 12, component=comp, reveal=1065)
        rt.sphere(f"Upper lab dome {i+1}", (x, y, 6.7), (.72,.72,.42), glass,
                  c.landmarks, 12, 7, component=comp, reveal=1065)
    records = []
    for i in range(11):
        a = math.tau*i/11
        records.append(rt.sphere(f"Punk Records lobe {i+1:02d}",
                                 (math.cos(a)*.92, math.sin(a)*.72, 11.52+(i%3)*.18),
                                 (.72, .6, .52), brain, c.landmarks, 12, 8,
                                 component="punk-records-attached", reveal=1066))
    for obj in records:
        obj["active_through_chapter"] = 1124.999
    return rt.finish("egghead-future-island-system", contract, c, rx, ry,
                     (19, -27, 19), (0, 0, 4.3), safe_full_chapter=1066,
                     layout_status="vertical_phase_stack_relative_topology")


def build_wano(contract, rx, ry):
    rt.reset(); c = rt.collections()
    sea = rt.material("M_Wano_Sea", "0c5b78", .2, emission="1388a3", emission_strength=.3)
    wall = rt.material("M_Wano_Wall", "62564c", .86)
    inland = rt.material("M_Wano_Inland", "26a8af", .2, emission="3ac6ca", emission_strength=.28)
    palettes = [
        rt.material("M_Wano_Kuri", "b65f3e", .76), rt.material("M_Wano_Udon", "8e9d43", .78),
        rt.material("M_Wano_Kibi", "d2a83d", .8), rt.material("M_Wano_Hakumai", "4d9761", .78),
        rt.material("M_Wano_Ringo", "7196a8", .72), rt.material("M_Wano_Capital", "b24d76", .72)
    ]
    snow = rt.material("M_Wano_Snow", "e2e7e5", .52)
    vermilion = rt.material("M_Wano_Vermilion", "b53025", .62,
                            emission="d03d2d", emission_strength=.18)
    roof = rt.material("M_Wano_Roof", "214d53", .58, metallic=.08)
    skull = rt.material("M_Onigashima_Skull", "aaa08e", .84)
    lava = rt.material("M_Onigashima_Lava", "c13f22", .34,
                       emission="ff5524", emission_strength=1.8)
    dark = rt.material("M_Onigashima_Rock", "292a31", .9)
    gold = rt.material("M_Wano_Gold", "d4a83b", .35, metallic=.55)
    flame = rt.material("M_Onigashima_Flame_Cloud", "d95b2b", .3,
                        emission="ff7837", emission_strength=2.4, alpha=.82)

    rt.island("Wano outer ocean", (0, 0, -.95), 16.2, .5, sea, c.topology,
              (1.2, .82), 64, component="wano-country", reveal=793)
    rt.torus("Wano colossal bowl wall", (-2.3, 1.0, 1.5), 8.2, .75, wall,
             c.topology, component="wano-walls", reveal=793)
    rt.cylinder("Wano raised bowl base", (-2.3, 1.0, .1), 8.35, 2.0, wall,
                c.topology, 64, scale_xy=(1.0,.84), component="wano-walls", reveal=793)
    rt.island("Wano inland sea", (-2.3, 1.0, 1.18), 7.55, .22, inland, c.topology,
              (1.0,.84), 64, component="wano-inland-sea", reveal=909)
    region_data = [
        ("kuri", (-6.1, -1.1), 2.25, palettes[0]),
        ("udon", (-1.1, -2.7), 2.05, palettes[1]),
        ("kibi", (2.4, -.4), 2.15, palettes[2]),
        ("hakumai", (1.1, 3.7), 2.05, palettes[3]),
        ("ringo", (-4.3, 4.6), 2.2, palettes[4]),
        ("flower-capital", (-2.2, 1.6), 2.0, palettes[5]),
    ]
    for idx, (name, (x,y), radius, mat) in enumerate(region_data):
        rt.island(f"Wano region {name}", (x,y,1.45), radius, .55, mat,
                  c.topology, (1.0,.78), 32, component=name, reveal=909)
        if name != "flower-capital":
            for j in range(5):
                rt.house(f"{name} village {j+1}",
                         (x+math.cos(math.tau*j/5)*radius*.55,
                          y+math.sin(math.tau*j/5)*radius*.38, 1.75),
                         .5, gold, roof, c.landmarks, component=name, reveal=909)
    rt.cone("Mount Fuji lower", (-2.4, 1.0, 4.25), 2.2, .42, 5.6, palettes[3],
            c.landmarks, vertices=40, component="mount-fuji", reveal=909)
    rt.cone("Mount Fuji snow cap", (-2.4, 1.0, 6.55), .92, .12, 1.7, snow,
            c.landmarks, vertices=40, component="mount-fuji", reveal=909)
    for i in range(7):
        a = math.tau*i/7
        pagoda(f"Flower Capital {i+1}",
               (-2.2+math.cos(a)*1.05, 1.6+math.sin(a)*.72, 1.9), .72,
               vermilion, roof, c.landmarks, "flower-capital", 909)
    for i in range(7):
        a = math.tau*i/7
        rt.curve(f"Wano waterfall {i+1}",
                 [(-2.3+math.cos(a)*8.2,1+math.sin(a)*6.9,1.5),
                  (-2.3+math.cos(a)*8.7,1+math.sin(a)*7.3,-.3)],
                 .18, inland, c.atmosphere, component="wano-walls", reveal=793)

    ox, oy = 8.7, -4.0
    onigashima_root = rt.island("Onigashima geographic root", (ox,oy,.2), 4.05, 1.25, dark,
                                c.topology, (1.0,.82), 44,
                                component="onigashima", reveal=793)
    rt.sphere("Onigashima skull dome", (ox,oy,3.0), (2.5,2.2,2.15), skull,
              c.landmarks, 24, 16, component="skull-dome", reveal=978)
    for side in (-1,1):
        horn = rt.cone(f"Onigashima horn {side:+}", (ox+side*2.1,oy,5.2),
                       .55,.06,3.3,dark,c.landmarks,vertices=20,
                       component="skull-dome",reveal=978)
        horn.rotation_euler[1] = side*.55
    for side in (-1,1):
        rt.sphere(f"Skull eye socket {side:+}", (ox+side*.82,oy-1.95,3.25),
                  (.55,.22,.62), dark, c.landmarks, 14,8,
                  component="skull-dome", reveal=978)
    rt.cube("Skull mouth gate", (ox,oy-2.05,1.65), (1.05,.22,.55), dark,
            c.landmarks, component="skull-dome", reveal=978)
    for i in range(4):
        torii(f"Onigashima port torii {i+1}", (ox-2.6+i*1.7, oy-4.1+i*.28, .45),
              .72, vermilion, c.landmarks, "onigashima-port", 978)
    rt.curve("Onigashima mountain road", [(ox-2.6,oy-3.4,.7),(ox-1.8,oy-2.0,1.1),
             (ox-.8,oy-1.0,1.5),(ox,oy-.5,1.8)], .12, gold, c.landmarks,
             component="onigashima-roads", reveal=978)
    blade = rt.beam("Onigashima giant katana", (ox+2.2,oy+.4,.55),
                    (ox+3.7,oy+.2,7.6), .18, gold, c.landmarks,
                    component="giant-katana", reveal=978)
    blade.scale.x = 1.5
    rt.cube("Katana guard", (ox+2.45,oy+.36,1.65), (.72,.18,.16), vermilion,
            c.landmarks, component="giant-katana", reveal=978)
    # Flame clouds are real scene geometry with a verified visibility window,
    # not a painted overlay. They travel with the island root from ch997-1048.
    flight_clouds = []
    for i in range(13):
        a = math.tau*i/13
        cloud_obj = rt.sphere(
            f"Onigashima flame cloud {i+1:02d}",
            (ox+math.cos(a)*3.25, oy+math.sin(a)*2.7, .1+(i%3)*.16),
            (.9, .58, .34), flame, c.states, 12, 7,
            component="onigashima-flame-clouds", reveal=997,
            confidence="verified_state_window", default_hidden=True,
        )
        cloud_obj["active_through_chapter"] = 1048.999
        flight_clouds.append(cloud_obj)
    cloud_ring = rt.torus("Onigashima flame cloud support ring", (ox,oy,.12),
                          3.4,.16,flame,c.states,
                          component="onigashima-flame-clouds", reveal=997,
                          confidence="verified_state_window", default_hidden=True)
    cloud_ring["active_through_chapter"] = 1048.999
    flight_clouds.append(cloud_ring)

    # Make the island, skull, port, roads, katana, and clouds one transformable
    # geographic hierarchy. The Wano country remains fixed in the same GLB.
    moving_components = {
        "onigashima", "skull-dome", "onigashima-port", "onigashima-roads",
        "giant-katana", "onigashima-flame-clouds",
    }
    for obj in list(bpy.context.scene.objects):
        if obj is onigashima_root or obj.get("component_id") not in moving_components:
            continue
        world = obj.matrix_world.copy()
        obj.parent = onigashima_root
        obj.matrix_world = world

    # The clip moves actual GLB geometry through the normalized Wano theatre.
    # Chapter-to-frame interpolation lives in the runtime manifest so scrubbing
    # backward restores the earlier geography deterministically.
    geographic_clip(onigashima_root, "onigashima_geographic_shift", [
        {"frame": 1, "location": (ox,oy,.2), "rotation": (0,0,0)},
        {"frame": 25, "location": (7.4,-3.2,5.0), "rotation": (0,.03,-.04)},
        {"frame": 70, "location": (-.5,.6,7.3), "rotation": (.02,.05,.10)},
        {"frame": 90, "location": (2.8,2.8,6.2), "rotation": (.02,.04,.17)},
        {"frame": 110, "location": (4.8,4.3,.8), "rotation": (0,.02,.20)},
        {"frame": 120, "location": (4.8,4.3,.8), "rotation": (0,.02,.20)},
        {"frame": 140, "location": (3.6,-1.0,-2.6), "rotation": (0,.02,.28)},
    ])
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 140
    bpy.context.scene["geographic_motion_owner"] = "chapter-sampled runtime track"
    bpy.context.scene["geographic_clip"] = "onigashima_geographic_shift"
    # Historical depth is modeled but withheld from the default view.
    rt.cylinder("Old Wano submerged silhouette", (-2.3,1.0,-2.0), 6.8, 2.4, wall,
                c.states, 40, scale_xy=(1,.82), component="old-wano-submerged",
                reveal=1055, confidence="cited_summary", default_hidden=True)
    result = rt.finish("wano-onigashima-country-system", contract, c, rx, ry,
                       (24,-29,22), (-.5,0,2.2), safe_full_chapter=978,
                       layout_status="regional_bowl_and_local_offshore_fortress_chapter_shifted")
    bpy.context.scene.frame_end = 140
    bpy.ops.wm.save_as_mainfile(filepath=str(rt.SOURCE / "wano-onigashima-country-system.blend"))
    result["blend_sha256"] = rt.sha(rt.SOURCE / "wano-onigashima-country-system.blend")
    result["named_clips"] = ["onigashima_geographic_shift"]
    result["geographic_checkpoints"] = [793, 997, 1027, 1039, 1049, 1109]
    return result


def build_elbaph(contract, rx, ry):
    rt.reset(); c = rt.collections()
    sea = rt.material("M_Elbaph_Sea", "152b55", .22, emission="223d70", emission_strength=.22)
    under = rt.material("M_Elbaph_Underworld", "41445a", .88)
    snow = rt.material("M_Elbaph_Snow", "becde0", .58, emission="98b8d8", emission_strength=.15)
    bark = rt.material("M_Adam_Bark", "5a3829", .92)
    green = rt.material("M_Elbaph_Sun_Green", "668641", .76)
    pine = rt.material("M_Elbaph_Pine", "173f39", .84)
    wood = rt.material("M_Elbaph_Wood", "7c4a2b", .82)
    gold = rt.material("M_Elbaph_Amber", "d5a64b", .48, metallic=.16,
                       emission="e2b65f", emission_strength=.18)
    roof = rt.material("M_Elbaph_Roof", "32433e", .74)
    cloud = rt.material("M_Elbaph_Cloud", "dae6ed", .58,
                        emission="b9d8f1", emission_strength=.25)
    mist = rt.material("M_Elbaph_Mist", "8aa8c9", .4, emission="7898bd",
                       emission_strength=.3, alpha=.55)

    rt.island("Elbaph sleeping-mist sea", (0,0,-1.1), 14.5, .45, sea, c.topology,
              (1.15,.8), 64, component="sleep-mist-route", reveal=1127)
    for i in range(14):
        a=math.tau*i/14
        rt.sphere(f"Sleeping mist bank {i+1:02d}", (math.cos(a)*10.5,math.sin(a)*7.2,.2+(i%3)*.2),
                  (2.1,1.2,.6),mist,c.atmosphere,12,7,
                  component="sleep-mist-route",reveal=1127)
    rt.island("Elbaph Underworld roots", (0,0,-.1), 8.2, 1.5, under, c.topology,
              (1.0,.78), 56, component="elbaph-underworld", reveal=1130)
    for i in range(26):
        a=math.tau*i/26; r=3.2+(i%4)*1.15
        rt.tree(f"Underworld pine {i+1:02d}", (math.cos(a)*r,math.sin(a)*r*.72,.7),
                .72+(i%3)*.12,bark,pine,c.landmarks,
                component="elbaph-underworld",reveal=1130)
    for i in range(9):
        a=math.tau*i/9
        rt.cone(f"Underworld snowy ridge {i+1}", (math.cos(a)*6.6,math.sin(a)*4.8,.85),
                1.15,.08,2.4,snow,c.landmarks,vertices=12,
                component="elbaph-underworld",reveal=1130)
    # A giant castle and a smaller bar provide scale without named characters.
    for tier in range(4):
        rt.cube(f"Road castle tier {tier+1}", (-4.2,-1.0,1.2+tier*.85),
                (1.15-tier*.12,.9-tier*.08,.45),under,c.landmarks,
                component="roads-castle",reveal=1130)
    rt.house("Ida bar", (4.3,-1.8,.85), 1.25, wood, roof, c.landmarks,
             component="idas-bar", reveal=1131)
    for i in range(3):
        x=-1.4+i*1.7; y=-4.6+(i%2)*.6
        rt.sphere(f"Giant fauna body {i+1}",(x,y,1.25),(1.1,.55,.65),under,c.landmarks,12,7,
                  component="giant-fauna-layer",reveal=1130)
        for leg in (-.6,.6):
            rt.cylinder(f"Giant fauna {i+1} leg {leg:+}",(x+leg,y, .62),.13,1.1,under,c.landmarks,8,
                        component="giant-fauna-layer",reveal=1130)

    # Treasure Tree Adam dominates all layers and owns the vertical connection.
    rt.cylinder("Treasure Tree Adam trunk", (0,0,8.3), 1.55, 16.2, bark,
                c.topology, 20, component="treasure-tree-adam", reveal=1132)
    for i in range(10):
        a=math.tau*i/10
        rt.beam(f"Adam root {i+1}",(0,0,.5),(math.cos(a)*7.2,math.sin(a)*5.5,.6),
                .32,bark,c.topology,component="treasure-tree-adam",reveal=1132)
    rt.island("Elbaph Sun World branch shelf", (0,0,10.5), 9.0, 1.15, green,
              c.topology,(1.12,.72),56,component="sun-world",reveal=1132)
    for i in range(12):
        a=math.tau*i/12
        rt.beam(f"Adam supporting branch {i+1}",(0,0,9.5),
                (math.cos(a)*8.4,math.sin(a)*5.9,10.25),.48,bark,c.topology,
                component="treasure-tree-adam",reveal=1132)
    for i in range(18):
        a=math.tau*i/18; r=3.4+(i%3)*1.8
        rt.house(f"Warland hall {i+1:02d}",(math.cos(a)*r,math.sin(a)*r*.62,11.1),
                 1.05+(i%4)*.1,wood,roof,c.landmarks,
                 component="warland-settlement",reveal=1132)
    for i in range(9):
        a=math.tau*i/9
        rt.torus(f"Warland shield {i+1}",(math.cos(a)*5.5,math.sin(a)*3.8,12.4),
                 .38,.12,gold,c.landmarks,rotation=(math.pi/2,0,0),
                 component="warland-settlement",reveal=1132)
    for i in range(16):
        a=math.tau*i/16
        rt.sphere(f"Adam upper canopy {i+1:02d}",(math.cos(a)*5.2,math.sin(a)*4.0,15.4+(i%4)*.45),
                  (2.4,1.8,1.4),green,c.landmarks,14,8,
                  component="treasure-tree-adam",reveal=1132)
    # Upper geography and current 1188 events remain withheld until receipt-level verification.
    for i in range(11):
        a=math.tau*i/11
        rt.sphere(f"Heaven World cloud {i+1:02d}",(math.cos(a)*4.5,math.sin(a)*3.5,18.2+(i%3)*.2),
                  (1.8,1.35,.7),cloud,c.states,12,7,
                  component="heaven-world",confidence="chapter_to_verify",default_hidden=True)
    rt.torus("Chapter 1188 event placeholder",(0,0,13.5),3.2,.18,gold,c.states,
             component="chapter-1188-current-state",confidence="chapter_to_verify",default_hidden=True)
    return rt.finish("elbaph-adam-world-system", contract, c, rx, ry,
                     (24,-31,24),(0,0,7.0),safe_full_chapter=1132,
                     layout_status="vertical_world_tree_canon_relationships_theory_overlay_excluded")


BUILDERS = {
    "egghead-future-island-system": build_egghead,
    "wano-onigashima-country-system": build_wano,
    "elbaph-adam-world-system": build_elbaph,
}


def main() -> int:
    options = args()
    rt.SOURCE.mkdir(parents=True, exist_ok=True)
    rt.RENDERS.mkdir(parents=True, exist_ok=True)
    selected = tuple(options.only or ASSETS)
    existing = {}
    if MANIFEST.exists():
        existing = {row["id"]: row for row in json.loads(MANIFEST.read_text())["assets"]}
    for asset_id in selected:
        contract = json.loads((ROOT / f"contracts/{asset_id}.visual.json").read_text())
        print(f"BUILD {asset_id}")
        existing[asset_id] = BUILDERS[asset_id](contract, options.resolution_x, options.resolution_y)
    payload = {
        "schema_version": 1,
        "generator": "scripts/build_endgame_island_batch.py",
        "definition": "chapter-gated LOD1 runtime world models; cited topology, normalized local scale",
        "assets": [existing[k] for k in ASSETS if k in existing],
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"MANIFEST={MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
