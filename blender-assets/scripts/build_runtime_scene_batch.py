#!/usr/bin/env python3
"""Build the missing contract-driven Blender scenes for the runtime batch.

This is intentionally a scene-system builder, not a generic island stamper.
Each function below encodes the relationships in one verified visual contract.
Unknown chapter variants remain editable in the .blend but are hidden from the
base GLB export. Runtime-visible objects carry glTF extras for component and
chapter gating.

Run with Blender 4.5+:
  Blender --background --python scripts/build_runtime_scene_batch.py -- \
    --resolution-x 1200 --resolution-y 900
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
RENDERS = ROOT / "renders/runtime"
MANIFEST = ROOT / "manifests/runtime-scene-builds.json"

ASSETS = (
    "totto-land",
    "world-government-tarai-system",
    "conomi-arlong-park",
    "arabasta-kingdom",
    "cactus-island-whisky-peak",
    "dressrosa-green-bit",
    "zou-zunesha",
    "amazon-lily",
    "mary-geoise-red-line",
    "sabaody-grove-network",
    "skypiea-sky-system",
)


@dataclass
class SceneCollections:
    topology: bpy.types.Collection
    landmarks: bpy.types.Collection
    states: bpy.types.Collection
    atmosphere: bpy.types.Collection
    lod: bpy.types.Collection


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=ASSETS)
    parser.add_argument("--resolution-x", type=int, default=1200)
    parser.add_argument("--resolution-y", type=int, default=900)
    return parser.parse_args(argv)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    value = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(value)
    return value


def collections() -> SceneCollections:
    return SceneCollections(
        collection("00_TOPOLOGY"),
        collection("10_LANDMARKS"),
        collection("20_EVENT_STATES"),
        collection("30_ATMOSPHERE_FX"),
        collection("40_RUNTIME_LOD"),
    )


def move(obj: bpy.types.Object, target: bpy.types.Collection) -> bpy.types.Object:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def material(name: str, color: str, roughness: float = .68, metallic: float = 0.0,
             emission: str | None = None, emission_strength: float = 0.0,
             alpha: float = 1.0) -> bpy.types.Material:
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    bsdf.inputs["Base Color"].default_value = (*rgb, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        ergb = tuple(int(emission[i:i + 2], 16) / 255 for i in (0, 2, 4))
        bsdf.inputs["Emission Color"].default_value = (*ergb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1:
        value.surface_render_method = "DITHERED"
    return value


def tag(obj: bpy.types.Object, component: str, reveal: int | None = None,
        *, confidence: str = "verified", default_hidden: bool = False) -> bpy.types.Object:
    obj["component_id"] = component
    obj["gate_confidence"] = confidence
    obj["default_hidden"] = default_hidden
    if reveal is not None:
        obj["reveal_chapter"] = reveal
    return obj


def cube(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float],
         mat: bpy.types.Material, target: bpy.types.Collection, **gate) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    if gate:
        tag(obj, **gate)
    return obj


def cylinder(name: str, loc: tuple[float, float, float], radius: float, depth: float,
             mat: bpy.types.Material, target: bpy.types.Collection, vertices: int = 32,
             scale_xy: tuple[float, float] = (1, 1), **gate) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale.x, obj.scale.y = scale_xy
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    if gate:
        tag(obj, **gate)
    return obj


def cone(name: str, loc: tuple[float, float, float], radius1: float, radius2: float,
         depth: float, mat: bpy.types.Material, target: bpy.types.Collection,
         vertices: int = 32, **gate) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2,
                                    depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    if gate:
        tag(obj, **gate)
    return obj


def sphere(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float],
           mat: bpy.types.Material, target: bpy.types.Collection, segments: int = 20,
           rings: int = 12, **gate) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    if gate:
        tag(obj, **gate)
    return obj


def torus(name: str, loc: tuple[float, float, float], major: float, minor: float,
          mat: bpy.types.Material, target: bpy.types.Collection,
          rotation: tuple[float, float, float] = (0, 0, 0), **gate) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=10,
                                     location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    if gate:
        tag(obj, **gate)
    return obj


def curve(name: str, points: list[tuple[float, float, float]], bevel: float,
          mat: bpy.types.Material, target: bpy.types.Collection, cyclic: bool = False,
          **gate) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel
    data.bevel_resolution = 2
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    spline.use_cyclic_u = cyclic
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    obj.data.materials.append(mat)
    target.objects.link(obj)
    if gate:
        tag(obj, **gate)
    return obj


def beam(name: str, start: tuple[float, float, float], end: tuple[float, float, float],
         width: float, mat: bpy.types.Material, target: bpy.types.Collection, **gate) -> bpy.types.Object:
    a, b = Vector(start), Vector(end)
    obj = cube(name, tuple((a + b) * .5), (width, width, (b - a).length / 2), mat, target)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    if gate:
        tag(obj, **gate)
    return obj


def island(name: str, loc: tuple[float, float, float], radius: float, depth: float,
           mat: bpy.types.Material, target: bpy.types.Collection,
           scale_xy: tuple[float, float] = (1, .82), vertices: int = 40, **gate) -> bpy.types.Object:
    return cylinder(name, loc, radius, depth, mat, target, vertices, scale_xy, **gate)


def house(prefix: str, loc: tuple[float, float, float], size: float,
          wall: bpy.types.Material, roof: bpy.types.Material,
          target: bpy.types.Collection, **gate) -> None:
    x, y, z = loc
    cube(f"{prefix} house", (x, y, z + size * .45), (size * .42, size * .34, size * .45), wall, target, **gate)
    top = cone(f"{prefix} roof", (x, y, z + size * 1.03), size * .58, 0, size * .42,
               roof, target, vertices=4, **gate)
    top.rotation_euler[2] = math.pi / 4


def tree(prefix: str, loc: tuple[float, float, float], size: float,
         trunk: bpy.types.Material, canopy: bpy.types.Material,
         target: bpy.types.Collection, **gate) -> None:
    x, y, z = loc
    cylinder(f"{prefix} trunk", (x, y, z + size * .45), size * .10, size * .9,
             trunk, target, vertices=10, **gate)
    sphere(f"{prefix} canopy", (x, y, z + size * 1.02), (size * .42, size * .38, size * .48),
           canopy, target, segments=14, rings=8, **gate)


def scene_settings(asset_id: str, resolution_x: int, resolution_y: int) -> Path:
    output = RENDERS / f"{asset_id}.png"
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.render.filepath = str(output)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world = bpy.data.worlds.new("Runtime World")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.008, .016, .028, 1)
    background.inputs["Strength"].default_value = .28
    scene.frame_start = 1
    scene.frame_end = 120
    return output


def camera_and_lights(location: tuple[float, float, float], target: tuple[float, float, float],
                      lens: float = 52) -> None:
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Runtime Camera")
    camera_data.lens = lens
    camera = bpy.data.objects.new("Runtime Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    lights = (
        ("Key", (-14, -16, 26), 1900, 11, (1.0, .77, .55)),
        ("Fill", (17, -2, 18), 1500, 13, (.38, .68, 1.0)),
        ("Rim", (2, 18, 23), 1750, 10, (.65, .82, 1.0)),
    )
    for name, loc, energy, size, color in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def finish(asset_id: str, contract: dict, cols: SceneCollections,
           resolution_x: int, resolution_y: int,
           camera: tuple[float, float, float], target: tuple[float, float, float],
           *, safe_full_chapter: int, layout_status: str = "contract_relationship_graph") -> dict:
    output = scene_settings(asset_id, resolution_x, resolution_y)
    camera_and_lights(camera, target)
    scene = bpy.context.scene
    scene["asset_id"] = asset_id
    scene["contract"] = f"contracts/{asset_id}.visual.json"
    scene["maturity"] = "runtime_blockout_v1"
    scene["runtime_export"] = True
    scene["safe_full_scene_chapter"] = safe_full_chapter
    scene["layout_status"] = layout_status
    blend = SOURCE / f"{asset_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    # The editable source keeps unresolved components modeled and addressable,
    # but a fallback PNG cannot carry per-node gates. Hide those objects for the
    # render; the saved .blend and subsequent GLB export retain them with
    # default_hidden=true in glTF extras for the app loader to enforce.
    fallback_hidden = [obj for obj in scene.objects if bool(obj.get("default_hidden", False))]
    for obj in fallback_hidden:
        obj.hide_render = True
    bpy.ops.render.render(write_still=True)
    for obj in fallback_hidden:
        obj.hide_render = False
    component_ids = sorted({str(obj.get("component_id")) for obj in scene.objects if obj.get("component_id")})
    return {
        "id": asset_id,
        "blend": f"source/{asset_id}.blend",
        "render": f"renders/runtime/{asset_id}.png",
        "contract": f"contracts/{asset_id}.visual.json",
        "maturity": "runtime_blockout_v1",
        "runtime_export": True,
        "safe_full_scene_chapter": safe_full_chapter,
        "layout_status": layout_status,
        "collections": [cols.topology.name, cols.landmarks.name, cols.states.name,
                        cols.atmosphere.name, cols.lod.name],
        "component_ids": component_ids,
        "objects": len(scene.objects),
        "blend_sha256": sha(blend),
        "render_sha256": sha(output),
        "contract_sha256": sha(ROOT / f"contracts/{asset_id}.visual.json"),
    }


def build_conomi(contract: dict, rx: int, ry: int) -> dict:
    reset(); c = collections()
    sea = material("M_Conomi_Sea", "0b5268", .28, metallic=.05)
    land = material("M_Conomi_Land", "4f6941", .85)
    wall = material("M_Arlong_Wall", "668d8e", .65)
    roof = material("M_Arlong_Roof", "a83e35", .6)
    village = material("M_Village", "d2b884", .78)
    wood = material("M_Wood", "6c432d", .74)
    water = material("M_Pool", "39a8b9", .2, emission="2c98ac", emission_strength=.6)
    island("Conomi sea stage", (0, 0, -.45), 12, .45, sea, c.topology, (1.15, .8), 64,
           component="conomi-islands", reveal=69)
    island("Arlong Park island", (4.4, .8, .05), 4.0, .65, land, c.topology,
           component="arlong-park", reveal=69)
    island("Cocoyasi island", (-4.9, -1.0, .02), 3.6, .55, land, c.topology,
           component="cocoyasi-village", reveal=70)
    for tier in range(4):
        z = .55 + tier * 1.05
        cube(f"Arlong headquarters tier {tier+1}", (4.4, .8, z),
             (1.25 - tier*.13, .9 - tier*.08, .46), wall, c.landmarks,
             component="arlong-park", reveal=69)
        cone(f"Arlong pagoda roof {tier+1}", (4.4, .8, z+.58), 1.65-tier*.15, 1.05-tier*.1,
             .26, roof, c.landmarks, vertices=8, component="arlong-park", reveal=69)
    torus("Arlong pool", (4.4, .8, .43), 1.8, .18, wall, c.landmarks,
          component="arlong-park", reveal=69)
    cylinder("Arlong water", (4.4, .8, .34), 1.65, .12, water, c.landmarks, 48,
             component="arlong-park", reveal=69)
    cube("Arlong map room", (4.4, .8, 2.62), (.74, .62, .32), wood, c.landmarks,
         component="arlong-map-room", reveal=69)
    for i in range(11):
        angle = math.tau*i/11
        house(f"Cocoyasi {i+1:02d}", (-4.9+math.cos(angle)*2.0, -1+math.sin(angle)*1.35, .35),
              .72, village, roof, c.landmarks, component="cocoyasi-village", reveal=70)
    curve("Conomi boat route", [(-8,-2,.5),(-2,-1.4,.45),(1,.2,.4),(3.2,.65,.4)], .08,
          water, c.topology, component="conomi-islands", reveal=69)
    return finish("conomi-arlong-park", contract, c, rx, ry, (16,-22,16), (0,0,1.8),
                  safe_full_chapter=70)


def build_arabasta(contract: dict, rx: int, ry: int) -> dict:
    reset(); c = collections()
    sand = material("M_Arabasta_Sand", "c89b54", .88)
    dune = material("M_Arabasta_Dune", "a96f34", .9)
    river = material("M_Sandora_River", "2e8fa3", .24, emission="2a8296", emission_strength=.35)
    stone = material("M_Alubarna_Stone", "d7c9a0", .76)
    roof = material("M_Arabasta_Roof", "9e5035", .72)
    oasis = material("M_Oasis", "2f785c", .48)
    dark = material("M_Tomb", "3b3028", .9)
    island("Arabasta landmass", (0,0,0), 10.8, .85, sand, c.topology, (1.1,.82), 64,
           component="arabasta-kingdom", reveal=113)
    for i in range(18):
        x = -8.2 + (i*3.17)%16.4; y = -5.6 + (i*2.29)%11.2
        cone(f"Sandora dune {i+1:02d}", (x,y,.62), 1.0+(i%3)*.18, .08, .55,
             dune, c.topology, vertices=24, component="sandora-desert", reveal=162)
    curve("Sandora River", [(-8,-6,.55),(-5,-3,.58),(-2,-1,.6),(1,1,.62),(4,3,.6),(8,5,.55)],
          .35, river, c.topology, component="sandora-river", reveal=161)
    # Alubarna is visibly elevated, with palace, clock tower, and tomb separate.
    cylinder("Alubarna rock plateau", (4.8,-1.2,1.2), 2.7, 2.0, dune, c.landmarks, 48,
             scale_xy=(1.0,.88), component="alubarna", reveal=129)
    for i in range(14):
        angle=math.tau*i/14
        house(f"Alubarna district {i+1:02d}", (4.8+math.cos(angle)*1.8,-1.2+math.sin(angle)*1.45,2.25),
              .55, stone, roof, c.landmarks, component="alubarna", reveal=129)
    cube("Alubarna palace", (4.8,-1.2,3.05), (1.0,.72,.62), stone, c.landmarks,
         component="alubarna-palace", reveal=129)
    cylinder("Alubarna clock tower", (3.8,-1.6,3.45), .22, 2.0, stone, c.landmarks, 12,
             component="alubarna-clock-tower", confidence="chapter_to_verify", default_hidden=True)
    cube("Tomb of the Kings", (4.8,-1.2,.15), (.8,.65,.28), dark, c.landmarks,
         component="tomb-of-the-kings", reveal=202)
    cities = [
        ("nanohana",(-7,-3.8),155,"port"), ("rainbase",(-2.8,3.2),126,"casino"),
        ("erumalu",(.1,-4.5),161,"ruin"), ("yuba",(-4.4,.2),162,"oasis"),
        ("katorea",(1.2,4.3),164,"camp"),
    ]
    for idx,(cid,(x,y),ch,kind) in enumerate(cities):
        cylinder(f"{cid} district", (x,y,.65), .9, .35, oasis if kind=="oasis" else stone,
                 c.landmarks, 24, component=cid, reveal=ch)
        for j in range(4 if kind!="ruin" else 2):
            house(f"{cid} {j+1}", (x+math.cos(j*1.7)*.55,y+math.sin(j*1.7)*.45,.82),
                  .34, stone, roof, c.landmarks, component=cid, reveal=ch)
    return finish("arabasta-kingdom", contract, c, rx, ry, (17,-23,19), (0,0,1.1),
                  safe_full_chapter=202)


def build_whisky(contract: dict, rx: int, ry: int) -> dict:
    reset(); c = collections()
    sea = material("M_Whisky_Sea", "0b5268", .28)
    rock = material("M_Sapoten_Rock", "7e5a3d", .9)
    land = material("M_Cactus_Land", "6c7842", .86)
    grave = material("M_Graves", "b9b29d", .84)
    town = material("M_Whisky_Town", "d0ad72", .78)
    roof = material("M_Whisky_Roof", "82412f", .7)
    river = material("M_Whisky_River", "3b9ab4", .25, emission="3b9ab4", emission_strength=.3)
    island("Cactus Island", (0,0,0), 8.5, .8, land, c.topology, (1.0,.78), 56,
           component="cactus-island", reveal=106)
    curve("Arrival river", [(0,-6.2,.52),(-.8,-3.3,.55),(.5,-1.3,.58),(0,0,.62)], .32,
          river, c.topology, component="whisky-peak-river-dock", reveal=106)
    cube("River dock", (0,-5.75,.62), (1.2,.35,.12), town, c.landmarks,
         component="whisky-peak-river-dock", reveal=106)
    for i in range(9):
        angle=math.tau*i/9
        x,y=math.cos(angle)*5.7,math.sin(angle)*4.0
        cone(f"Sapoten grave mountain {i+1:02d}", (x,y,2.0), 1.15,.35,3.2,rock,c.landmarks,24,
             component="sapoten-graveyard", reveal=107)
        # Rock arms make the skyline read as cactus-like without literal plants.
        beam(f"Sapoten arm A {i+1:02d}",(x,y,2.2),(x+math.cos(angle+.9)*1.0,y+math.sin(angle+.9)*.7,2.8),
             .22,rock,c.landmarks,component="sapoten-graveyard",reveal=107)
        beam(f"Sapoten arm B {i+1:02d}",(x,y,1.7),(x+math.cos(angle-.9)*.8,y+math.sin(angle-.9)*.6,2.25),
             .19,rock,c.landmarks,component="sapoten-graveyard",reveal=107)
        for g in range(5):
            cube(f"Grave {i+1:02d}-{g+1}",(x+(g-2)*.16,y-.25,3.25+g*.05),(.055,.025,.16),grave,c.landmarks,
                 component="sapoten-graveyard",reveal=107)
    for i in range(16):
        angle=math.tau*i/16
        house(f"Whisky Peak {i+1:02d}",(math.cos(angle)*2.35,math.sin(angle)*1.55,.55),.48,
              town,roof,c.landmarks,component="whisky-peak",reveal=106)
    return finish("cactus-island-whisky-peak", contract, c, rx, ry, (14,-20,15), (0,0,1.5),
                  safe_full_chapter=107)


def build_dressrosa(contract: dict, rx: int, ry: int) -> dict:
    reset(); c = collections()
    sea=material("M_Dressrosa_Sea","135c72",.25)
    land=material("M_Dressrosa_Land","98794d",.84)
    green=material("M_GreenBit","2f7048",.78)
    stone=material("M_Dressrosa_Stone","d0b184",.72)
    roof=material("M_Dressrosa_Roof","b84d45",.68)
    iron=material("M_Iron_Bridge","4d5257",.38,metallic=.7)
    flower=material("M_Flowers","d34f7a",.58,emission="a73567",emission_strength=.25)
    factory=material("M_SMILE_Factory","4c4542",.5,metallic=.25)
    island("Dressrosa", (0,-1,0), 7.3,.9,land,c.topology,(1.05,.82),56,
           component="dressrosa",reveal=682)
    island("Green Bit", (0,7.1,.1), 3.0,.7,green,c.topology,(1.15,.8),44,
           component="green-bit",reveal=710)
    beam("Green Bit iron bridge",(0,4.55,.7),(0,6.0,.7),.16,iron,c.landmarks,
         component="green-bit-iron-bridge",reveal=710)
    for x in (-.35,.35):
        beam(f"Bridge rail {x:+}",(x,4.5,1.05),(x,6.05,1.05),.06,iron,c.landmarks,
             component="green-bit-iron-bridge",reveal=710)
    # Central crown plateau; palace stays on it in the verified pre-Pica state.
    cylinder("Kings Plateau", (0,-.7,1.35),2.1,2.1,stone,c.landmarks,12,
             component="kings-plateau",reveal=682)
    cube("Royal Palace",(0,-.7,3.0),(1.0,.72,.7),stone,c.landmarks,
         component="dressrosa-royal-palace",reveal=682)
    for i in range(8):
        angle=math.tau*i/8
        cone(f"Crown spire {i+1}",(math.cos(angle)*1.65,-.7+math.sin(angle)*1.65,2.55),.22,0,.75,
             roof,c.landmarks,12,component="kings-plateau",reveal=682)
    torus("Corrida Colosseum",(-3.9,-1.4,.95),1.15,.34,stone,c.landmarks,
          component="corrida-colosseum",reveal=702)
    sphere("Flower Hill",(3.5,1.5,.85),(1.45,1.1,.7),green,c.landmarks,
           component="flower-hill",reveal=701)
    for i in range(22):
        angle=math.tau*i/22
        sphere(f"Flower patch {i+1:02d}",(3.5+math.cos(angle)*1.0,1.5+math.sin(angle)*.75,1.45),(.13,.13,.13),
               flower,c.landmarks,12,6,component="flower-hill",reveal=701)
    cube("SMILE Factory underground",(-1.8,1.8,-.25),(1.15,.8,.38),factory,c.landmarks,
         component="smile-factory",reveal=738)
    for i in range(24):
        angle=math.tau*i/24
        house(f"Dressrosa district {i+1:02d}",(math.cos(angle)*4.8,-1+math.sin(angle)*3.5,.55),.4,
              stone,roof,c.landmarks,component="dressrosa",reveal=682)
    return finish("dressrosa-green-bit", contract, c, rx, ry, (16,-23,18), (0,1.2,1.4),
                  safe_full_chapter=738)


def build_zou(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    hide=material("M_Zunesha_Hide","6d6259",.93)
    tusk=material("M_Zunesha_Tusk","ded5bd",.55)
    land=material("M_Zou_Land","496b43",.83)
    city=material("M_Mokomo","c6a86d",.76)
    roof=material("M_Mokomo_Roof","8f5745",.72)
    water=material("M_Eruption_Rain","68cce2",.18,emission="65cce5",emission_strength=.8)
    cloud=material("M_Zou_Mist","c9d5db",.8,alpha=.42)
    # Two-jointed legs reach through sea mist to the implied seafloor.
    leg_xy=[(-3,-1.4),(-3,1.4),(3,-1.4),(3,1.4)]
    for i,(x,y) in enumerate(leg_xy):
        beam(f"Zunesha upper leg {i+1}",(x,y,13),(x*1.05,y*1.1,7),.58,hide,c.topology,
             component="zunesha-legs",reveal=795)
        beam(f"Zunesha lower leg {i+1}",(x*1.05,y*1.1,7),(x*.92,y*1.05,.2),.42,hide,c.topology,
             component="zunesha-legs",reveal=795)
        sphere(f"Zunesha knee {i+1}",(x*1.05,y*1.1,7),(.72,.62,.68),hide,c.topology,
               component="zunesha-legs",reveal=795)
    sphere("Zunesha body",(0,0,14.7),(5.1,2.7,2.25),hide,c.topology,
           component="zunesha",reveal=795)
    sphere("Zunesha head",(-5.0,-.05,14.5),(2.0,2.35,2.7),hide,c.topology,
           component="zunesha",reveal=795)
    sphere("Zunesha ear L",(-4.7,-2.1,14.8),(1.3,.28,1.75),hide,c.topology,
           component="zunesha",reveal=795)
    sphere("Zunesha ear R",(-4.7,2.1,14.8),(1.3,.28,1.75),hide,c.topology,
           component="zunesha",reveal=795)
    curve("Zunesha trunk",[(-6.2,0,14),(-7.2,0,11),(-6.7,0,7.5),(-5.4,0,6.2)],.52,hide,c.topology,
          component="zunesha-trunk",reveal=795)
    for y in (-.68,.68):
        cone(f"Zunesha tusk {y:+}",(-6.4,y,13.2),.25,0,2.1,tusk,c.landmarks,16,
             component="zunesha",reveal=795).rotation_euler[1]=math.pi/2
    island("Zou on back",(.4,0,17.0),4.25,.55,land,c.landmarks,(1.0,.58),48,
           component="zou",reveal=795)
    for i in range(22):
        angle=math.tau*i/22
        house(f"Mokomo district {i+1:02d}",(.4+math.cos(angle)*2.7,math.sin(angle)*1.25,17.32),.38,
              city,roof,c.landmarks,component="mokomo-dukedom",reveal=804)
    # Verified eruption rain at the encounter gate.
    for i in range(5):
        curve(f"Eruption rain arc {i+1}",[(-5.4,0,6.2),(-4+i*.8,-1.5+i*.7,12),(0+i*.5,-1+i*.4,18.6)],
              .09,water,c.atmosphere,component="zunesha-trunk",reveal=795)
    for i in range(10):
        sphere(f"Cloud bank {i+1}",(-7+i*1.5,(-1)**i*2.4,8.4+(i%3)*.35),(1.4,1.0,.55),cloud,c.atmosphere,
               component="zunesha",reveal=795)
    return finish("zou-zunesha", contract, c, rx, ry, (25,-32,20), (-.5,0,10),
                  safe_full_chapter=804,layout_status="moving_entity_local_scene")


def build_amazon_lily(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    rock=material("M_Amazon_Rock","605443",.9)
    jungle=material("M_Amazon_Jungle","2b6544",.82)
    wall=material("M_Kuja_Stone","c09a70",.76)
    roof=material("M_Kuja_Roof","9b3f42",.7)
    gold=material("M_Kuja_Gold","d7af54",.42,metallic=.45)
    water=material("M_Calm_Belt","164e63",.22)
    island("Calm Belt stage",(0,0,-.6),11,.45,water,c.topology,(1.0,.78),64,
           component="amazon-lily",reveal=514)
    cone("Amazon Lily mountain",(0,0,2.3),7.2,4.8,5.4,rock,c.topology,64,
         component="amazon-lily",reveal=514)
    # The torus/rim and recessed floor make the city a hidden mountain-top bowl.
    torus("Mountain bowl rim",(0,0,5.2),4.15,.72,rock,c.landmarks,
          component="amazon-lily-mountain-bowl",reveal=514)
    cylinder("Mountain bowl floor",(0,0,4.35),3.6,.45,jungle,c.landmarks,56,
             scale_xy=(1.0,.82),component="amazon-lily-mountain-bowl",reveal=514)
    for i in range(28):
        angle=math.tau*i/28
        radius=2.6 if i%2 else 1.65
        house(f"Kuja village {i+1:02d}",(math.cos(angle)*radius,math.sin(angle)*radius*.72,4.62),.38,
              wall,roof,c.landmarks,component="kuja-village",reveal=514)
    cube("Kuja Palace",(0,.35,5.45),(1.15,.78,.82),wall,c.landmarks,
         component="kuja-palace",reveal=514)
    for i in range(34):
        angle=math.tau*i/34
        tree(f"Jungle {i+1:02d}",(math.cos(angle)*5.4,math.sin(angle)*4.1,4.35-(i%3)*.15),.58,
             rock,jungle,c.landmarks,component="amazon-lily",reveal=514)
    # Serpent culture appears as sculpture, never as the landmass silhouette.
    curve("Kuja serpent sculpture",[(-1.8,-.8,5.0),(-1.0,-1.2,5.5),(0,-.9,5.1),(1,-1.2,5.6),(1.8,-.8,5.2)],
          .12,gold,c.landmarks,component="kuja-village",reveal=514)
    return finish("amazon-lily", contract, c, rx, ry, (15,-22,16), (0,0,3.3),
                  safe_full_chapter=514)


def build_mary_geoise(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    red=material("M_Red_Line","7b3d32",.93)
    summit=material("M_MaryGeoise_Stone","d8d2c4",.78)
    roof=material("M_Pangaea_Roof","59718a",.68)
    gold=material("M_Bondola","d9b55c",.4,metallic=.4)
    sea=material("M_RedPort_Sea","0b3c55",.25)
    cube("Red Line continental wall",(0,0,5.5),(5.2,3.1,5.5),red,c.topology,
         component="red-line-summit",reveal=142)
    cube("Summit city plateau",(0,0,11.15),(5.6,3.5,.22),summit,c.landmarks,
         component="mary-geoise",reveal=142)
    for side,y in enumerate((-2.5,2.5)):
        for i in range(9):
            house(f"Summit district {side+1}-{i+1:02d}",(-4+i, y,11.36),.52,summit,roof,c.landmarks,
                  component="mary-geoise",reveal=142)
    cube("Pangaea Castle",(0,0,12.35),(1.65,1.25,1.15),summit,c.landmarks,
         component="pangaea-castle",reveal=142)
    for x in (-1.35,1.35):
        cylinder(f"Pangaea tower {x:+}",(x,0,13.0),.48,2.0,summit,c.landmarks,16,
                 component="pangaea-castle",reveal=142)
        cone(f"Pangaea roof {x:+}",(x,0,14.15),.65,0,.6,roof,c.landmarks,16,
             component="pangaea-castle",reveal=142)
    for side,y,cid in ((-1,-4.1,"red-port-paradise"),(1,4.1,"red-port-new-world")):
        island(f"{cid} water",(0,y,.05),4.2,.2,sea,c.topology,(1,.45),40,component=cid,confidence="chapter_to_verify")
        cube(f"{cid} port",(0,y,.45),(2.1,.55,.35),summit,c.landmarks,component=cid,confidence="chapter_to_verify")
        for x in (-1.4,1.4):
            curve(f"Bondola cable {cid} {x:+}",[(x,y,.8),(x,y*.55,5.5),(x,y*.2,10.9)],.055,gold,c.landmarks,
                  component="bondola-route",confidence="chapter_to_verify")
            for z in (3.0,6.0,9.0):
                cube(f"Bondola cabin {cid} {x:+} {z}",(x,y*(1-z/12),z),(.26,.2,.32),gold,c.landmarks,
                     component="bondola-route",confidence="chapter_to_verify")
    return finish("mary-geoise-red-line",contract,c,rx,ry,(19,-25,16),(0,0,6.3),
                  safe_full_chapter=142,layout_status="vertical_cross_section")


def build_sabaody(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    root=material("M_Yarukiman_Root","6d4a35",.9)
    canopy=material("M_Yarukiman_Canopy","3a7050",.78)
    grass=material("M_Grove_Ground","6f8b55",.82)
    bridge=material("M_Root_Bridge","9a7048",.74)
    bubble=material("M_Resin_Bubble","9ee9ef",.18,emission="7bdce5",emission_strength=.5,alpha=.28)
    park=material("M_Sabaody_Park","dc7b8e",.58)
    auction=material("M_Auction_House","77554c",.75)
    positions=[]
    # Contract proves 79 numbered roots, not their exact plan. A compact golden-angle
    # network makes every grove addressable while declaring itself schematic.
    golden=math.pi*(3-math.sqrt(5))
    for i in range(79):
        r=1.0+math.sqrt(i)*.82
        a=i*golden
        x,y=math.cos(a)*r,math.sin(a)*r*.72
        positions.append((x,y))
        island(f"Grove {i+1:02d} root island",(x,y,.12),.48+(i%4)*.035,.34,grass,c.topology,(1,.82),20,
               component="yarukiman-mangroves",reveal=496)
        cylinder(f"Grove {i+1:02d} mangrove",(x,y,1.2),.18+(i%3)*.018,2.1,root,c.landmarks,12,
                 component="yarukiman-mangroves",reveal=496)
        sphere(f"Grove {i+1:02d} canopy",(x,y,2.35),(.72,.62,.58),canopy,c.landmarks,14,8,
               component="yarukiman-mangroves",reveal=496)
        if i%3==0:
            sphere(f"Grove {i+1:02d} bubble",(x+.42,y-.28,2.0+(i%5)*.16),(.22,.22,.22),bubble,c.atmosphere,12,8,
                   component="sabaody-bubble-layer",reveal=496)
        if i>0:
            parent=max(0,int(i-math.sqrt(i)*1.7))
            px,py=positions[parent]
            curve(f"Root bridge {parent+1:02d}-{i+1:02d}",[(px,py,.58),((px+x)/2,(py+y)/2,.76),(x,y,.58)],
                  .055,bridge,c.topology,component="sabaody-root-bridges",reveal=496)
    px,py=positions[20]
    torus("Sabaody Park wheel",(px,py,1.7),.7,.08,park,c.landmarks,rotation=(math.pi/2,0,0),
          component="sabaody-park",reveal=499)
    ax,ay=positions[37]
    cube("Human Auctioning House",(ax,ay,1.0),(.7,.55,.6),auction,c.landmarks,
         component="human-auctioning-house",reveal=501)
    return finish("sabaody-grove-network",contract,c,rx,ry,(18,-25,20),(0,0,1.0),
                  safe_full_chapter=501,layout_status="relationship_schematic_not_canon_bearings")


def build_skypiea(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    cloud=material("M_Island_Cloud","dbe7ec",.72)
    cloud_shadow=material("M_Cloud_Shadow","8ca6b5",.82)
    earth=material("M_Upper_Yard","61734b",.86)
    ruin=material("M_Shandora","a68e5d",.78)
    gold=material("M_Belfry_Gold","d7b85a",.4,metallic=.48,emission="d2a93c",emission_strength=.3)
    vine=material("M_Giant_Jack","3d7043",.8)
    water=material("M_White_White_Sea","c8e1ec",.36,alpha=.75)
    island("White-White Sea",(0,0,-.25),11,.42,water,c.topology,(1.15,.78),64,
           component="white-white-sea",reveal=239)
    # Cloud ocean is composed of overlapping volumes rather than a flat white disc.
    for i in range(24):
        x=-8+(i*3.13)%16; y=-5+(i*1.91)%10
        sphere(f"Cloud sea puff {i+1:02d}",(x,y,.12+(i%3)*.08),(1.4,1.0,.38),cloud,c.topology,14,8,
               component="white-white-sea",reveal=239)
    for i in range(10):
        angle=math.tau*i/10
        sphere(f"Angel Island cloud {i+1:02d}",(-4+math.cos(angle)*2.1,-.7+math.sin(angle)*1.4,1.3),
               (1.25,1.0,.52),cloud,c.landmarks,16,8,component="angel-island",reveal=239)
    for i in range(18):
        angle=math.tau*i/18
        house(f"Angel settlement {i+1:02d}",(-4+math.cos(angle)*1.65,-.7+math.sin(angle)*1.0,1.62),.34,
              cloud_shadow,gold,c.landmarks,component="angel-island",reveal=239)
    island("Upper Yard solid land",(3.2,.6,1.3),4.0,.8,earth,c.landmarks,(1.0,.72),48,
           component="upper-yard",reveal=239)
    for i in range(12):
        angle=math.tau*i/12
        cube(f"Shandora ruin {i+1:02d}",(3.2+math.cos(angle)*2.1,.6+math.sin(angle)*1.3,2.05),(.22,.22,.55),
             ruin,c.landmarks,component="shandora",reveal=268)
    # Late landmarks stay authored in the source but are hidden from the base export.
    late=collection("Giant_Jack_And_Belfry_GATE_TBD",c.states)
    late.hide_render=True; late.hide_viewport=True
    curve("Giant Jack",[(3.2,.6,1.8),(2.8,.4,5),(3.5,.7,9),(3.0,.5,13)],.42,vine,late,
          component="giant-jack",confidence="chapter_to_verify",default_hidden=True)
    for i in range(7):
        sphere(f"Belfry cloud {i+1}",(3+math.cos(i)*1.5,.5+math.sin(i)*.9,12.6),(.95,.72,.35),cloud,late,14,8,
               component="golden-belfry-cloud",confidence="chapter_to_verify",default_hidden=True)
    cube("Golden Belfry",(3,.5,13.15),(.55,.42,.75),gold,late,
         component="golden-belfry-cloud",confidence="chapter_to_verify",default_hidden=True)
    return finish("skypiea-sky-system",contract,c,rx,ry,(17,-24,17),(0,0,2.0),
                  safe_full_chapter=268,layout_status="layered_sky_local_scene")


def build_totto(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    ocean=material("M_Totto_Ocean","173f62",.25)
    sponge=material("M_Cake_Sponge","d6a15e",.72)
    cream=material("M_Cake_Cream","f0d8c3",.55)
    berry=material("M_Cake_Berry","bd3e60",.56)
    chocolate=material("M_Chocolate","5b3428",.72)
    green=material("M_Food_Green","6f8b4c",.76)
    gold=material("M_Sugar_Gold","d7b555",.45,metallic=.2)
    pastel=material("M_Candy","d77ca0",.48)
    ice=material("M_Ice","9bd7e3",.32,alpha=.85)
    island("Totto Land ocean stage",(0,0,-.6),15,.35,ocean,c.topology,(1.0,.8),64,
           component="totto-land",reveal=651)
    for tier,(r,z,mat) in enumerate(((3.5,.2,sponge),(2.7,.95,cream),(1.9,1.65,sponge),(1.1,2.3,cream))):
        cylinder(f"Whole Cake tier {tier+1}",(0,0,z),r,.7,mat,c.landmarks,48,
                 component="whole-cake-island",reveal=651)
    cube("Whole Cake Chateau",(0,0,3.2),(.9,.72,.92),cream,c.landmarks,
         component="whole-cake-chateau",reveal=651)
    for i in range(8):
        angle=math.tau*i/8
        sphere(f"Whole Cake berry {i+1}",(math.cos(angle)*1.2,math.sin(angle)*1.2,2.8),(.24,.24,.24),berry,c.landmarks,12,8,
               component="whole-cake-island",reveal=651)

    theme_mats={"cacao":chocolate,"tea":green,"coffee":chocolate,"biscuits":gold,"candy":pastel,
                "cheese":gold,"fruits":berry,"ice":ice,"jam":berry,"jelly":pastel,"flour":cream,
                "whipped-cream":cream,"meringue":cream,"nuts":chocolate,"beans":green,"seeds":green}
    directions={"north":math.pi/2,"northeast":math.pi/4,"east":0,"southeast":-math.pi/4,
                "south":-math.pi/2,"southwest":-3*math.pi/4,"west":math.pi,"northwest":3*math.pi/4}
    subsidiaries=contract["identity"]["subsidiaries"]
    unknown_slot=0
    for i,item in enumerate(subsidiaries):
        placement=item["relative_placement"]
        direction=placement.get("direction")
        if direction:
            base=directions[direction]
            angle=base+((i%5)-2)*.11
        else:
            angle=unknown_slot*math.tau/17+.17
            unknown_slot+=1
        ring=placement.get("ring")
        radius=6.2 if ring=="innermost" else 12.2 if ring=="outermost" else 8.3+(i%3)*1.25
        x,y=math.cos(angle)*radius,math.sin(angle)*radius*.68
        theme=item["theme_hint"].get("theme","design")
        mat=theme_mats.get(theme,sponge if i%2 else green)
        ch=item.get("debut_chapter")
        gate = ({"component": item["slug"], "reveal": ch} if ch is not None else
                {"component": item["slug"], "confidence": "chapter_to_verify", "default_hidden": True})
        # Every subsidiary gets a distinct footprint and accent recipe.
        vertices=5+(i%7)
        base_obj=island(f"{item['name']} addressable island",(x,y,.02),.62+(i%4)*.1,.42,mat,c.topology,
                        (1.0+(i%3)*.12,.72+(i%5)*.05),vertices,**gate)
        base_obj["theme_hint"]=theme
        base_obj["relative_placement_status"]=placement.get("medium","unresolved")
        if theme in {"candy","jelly","jam","fruits","eggs"}:
            for j in range(2+(i%3)):
                sphere(f"{item['slug']} accent {j+1}",(x+(j-1)*.24,y, .58+j*.12),(.22,.22,.25),
                       pastel if theme!="fruits" else berry,c.landmarks,12,8,**gate)
        elif theme in {"biscuits","piepie","browned-food","package","cutlery"}:
            for j in range(2+(i%2)):
                cube(f"{item['slug']} accent {j+1}",(x,y,.54+j*.25),(.34-j*.04,.28-j*.03,.11),
                     gold,c.landmarks,**gate).rotation_euler[2]=j*.35
        else:
            cone(f"{item['slug']} themed hill",(x,y,.65),.48,.14,.9,
                 mat,c.landmarks,vertices=vertices,**gate)
    safe=max([651]+[x["debut_chapter"] for x in subsidiaries if x.get("debut_chapter") is not None])
    return finish("totto-land",contract,c,rx,ry,(21,-31,24),(0,0,1.2),
                  safe_full_chapter=safe,layout_status="authored_direction_when_known_unknowns_schematic")


def build_tarai(contract: dict, rx: int, ry: int) -> dict:
    reset(); c=collections()
    ocean=material("M_Tarai_Ocean","0b3f5b",.24)
    current=material("M_Tarai_Current","55c6dc",.2,emission="48bdd6",emission_strength=.75)
    justice=material("M_WG_Stone","c9c6b8",.75)
    marine=material("M_Marineford","d7d1bd",.72)
    prison=material("M_Impel_Iron","31383d",.42,metallic=.5)
    lava=material("M_Impel_Core","8c3728",.42,emission="e15e34",emission_strength=2.0)
    island("Tarai Current stage",(0,0,-.6),13,.45,ocean,c.topology,(1.0,.8),64,
           component="tarai-current",reveal=522)
    triangle=[(-6,-3),(6,-3),(0,5.2)]
    # Curved motion, never straight atlas-coordinate connectors.
    for ring in (3.0,4.2,5.4):
        pts=[]
        for i in range(12):
            a=math.tau*i/12
            pts.append((math.cos(a)*ring,math.sin(a)*ring*.72,.15+(i%2)*.05))
        curve(f"Tarai current ring {ring}",pts,.16,current,c.topology,cyclic=True,
              component="tarai-current",reveal=522)
    # Marineford: crescent bay and tiered fortress.
    mx,my=triangle[0]
    torus("Marineford crescent bay",(mx,my,.4),2.0,.48,marine,c.landmarks,
          component="marineford",reveal=94)
    cube("Marineford fortress",(mx,my+.5,1.45),(1.5,.72,.9),marine,c.landmarks,
         component="marineford",reveal=94)
    for i in range(5):
        cylinder(f"Marineford tower {i+1}",(mx-1.2+i*.6,my+.2,2.35),.22,1.3,marine,c.landmarks,12,
                 component="marineford",reveal=94)
    # Enies Lobby: court island over a visible void.
    ex,ey=triangle[1]
    torus("Enies Lobby abyss",(ex,ey,.1),1.65,.32,prison,c.landmarks,
          component="enies-lobby",reveal=358)
    island("Enies Lobby court",(ex,ey,1.05),1.35,.55,justice,c.landmarks,(1,.75),32,
           component="enies-lobby",reveal=358)
    cube("Tower of Justice",(ex,ey,2.0),(.62,.55,.75),justice,c.landmarks,
         component="enies-lobby",reveal=358)
    # Impel Down is a depth column, not an ordinary island.
    ix,iy=triangle[2]
    cylinder("Impel Down surface cap",(ix,iy,.5),1.2,.7,justice,c.landmarks,32,
             component="impel-down",reveal=525)
    for level in range(6):
        z=-.2-level*.85
        cylinder(f"Impel Down level {level+1}",(ix,iy,z),1.0-level*.08,.65,prison,c.landmarks,24,
                 component="impel-down",reveal=525)
    sphere("Impel inferno core",(ix,iy,-5.2),(.72,.72,.72),lava,c.landmarks,16,8,
           component="impel-down",reveal=525)
    # Three distributed gates control entry to the current.
    for i,(x,y) in enumerate(((-2.6,-4.5),(3.2,-4.2),(0,3.0))):
        for side in (-.7,.7):
            cube(f"Gate of Justice {i+1} pier {side:+}",(x+side,y,1.15),(.3,.42,1.15),justice,c.landmarks,
                 component="gates-of-justice",reveal=376)
        beam(f"Gate of Justice {i+1} lintel",(x-.9,y,2.3),(x+.9,y,2.3),.24,justice,c.landmarks,
             component="gates-of-justice",reveal=376)
    return finish("world-government-tarai-system",contract,c,rx,ry,(18,-25,18),(0,0,-.2),
                  safe_full_chapter=525,layout_status="relational_triangle_exact_bearings_unknown")


BUILDERS = {
    "totto-land": build_totto,
    "world-government-tarai-system": build_tarai,
    "conomi-arlong-park": build_conomi,
    "arabasta-kingdom": build_arabasta,
    "cactus-island-whisky-peak": build_whisky,
    "dressrosa-green-bit": build_dressrosa,
    "zou-zunesha": build_zou,
    "amazon-lily": build_amazon_lily,
    "mary-geoise-red-line": build_mary_geoise,
    "sabaody-grove-network": build_sabaody,
    "skypiea-sky-system": build_skypiea,
}


def main() -> int:
    args = cli_args()
    SOURCE.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    selected = tuple(args.only or ASSETS)
    existing = {}
    if MANIFEST.exists():
        existing = {x["id"]: x for x in json.loads(MANIFEST.read_text())["assets"]}
    for asset_id in selected:
        contract_path = ROOT / f"contracts/{asset_id}.visual.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        print(f"BUILD {asset_id}")
        existing[asset_id] = BUILDERS[asset_id](contract, args.resolution_x, args.resolution_y)
    payload = {
        "schema_version": 1,
        "generator": "scripts/build_runtime_scene_batch.py",
        "definition": "loader-ready procedural runtime blockouts; not final cinematic art",
        "assets": [existing[k] for k in ASSETS if k in existing],
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST={MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
