#!/usr/bin/env python3
"""Build editable Blender blockouts for Loguetown and the Water 7 rail system.

These are evidence-constrained blockouts, not runtime exports. Water 7 route
bearings are deliberately schematic until panel-level route geometry is
verified. The app repository is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
RENDERS = ROOT / "renders/blockouts"
MANIFEST = ROOT / "manifests/narrative-blockouts.json"
CONTRACTS = ROOT / "contracts"
ASSETS = ("loguetown-roger-execution", "water-7-sea-train-network")


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=ASSETS)
    parser.add_argument("--resolution-x", type=int, default=1400)
    parser.add_argument("--resolution-y", type=int, default=900)
    return parser.parse_args(argv)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    value = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(value)
    return value


def move(obj: bpy.types.Object, target: bpy.types.Collection) -> bpy.types.Object:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def tag_runtime(obj: bpy.types.Object, component_id: str, reveal_chapter: int | None = None,
                *, confidence: str = "verified", default_hidden: bool = False) -> bpy.types.Object:
    """Attach the node extras consumed by the MapLibre runtime gate."""
    obj["component_id"] = component_id
    obj["gate_confidence"] = confidence
    obj["default_hidden"] = default_hidden
    if reveal_chapter is not None:
        obj["reveal_chapter"] = reveal_chapter
    return obj


def mat(name: str, hex_value: str, roughness: float = .6, metallic: float = 0.0,
        emission: str | None = None, emission_strength: float = 0.0) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    rgb = tuple(int(hex_value[i:i + 2], 16) / 255 for i in (0, 2, 4))
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        ergb = tuple(int(emission[i:i + 2], 16) / 255 for i in (0, 2, 4))
        bsdf.inputs["Emission Color"].default_value = (*ergb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return value


def cube(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
         material: bpy.types.Material, target: bpy.types.Collection) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return move(obj, target)


def cylinder(name: str, location: tuple[float, float, float], radius: float, depth: float,
             material: bpy.types.Material, target: bpy.types.Collection, vertices: int = 32) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return move(obj, target)


def cone(name: str, location: tuple[float, float, float], radius1: float, radius2: float,
         depth: float, material: bpy.types.Material, target: bpy.types.Collection,
         vertices: int = 48) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2,
                                    depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return move(obj, target)


def sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
           material: bpy.types.Material, target: bpy.types.Collection) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return move(obj, target)


def beam(name: str, start: tuple[float, float, float], end: tuple[float, float, float],
         width: float, material: bpy.types.Material, target: bpy.types.Collection) -> bpy.types.Object:
    a, b = Vector(start), Vector(end)
    midpoint = (a + b) * .5
    length = (b - a).length
    obj = cube(name, tuple(midpoint), (width, width, length / 2), material, target)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def curve(name: str, points: list[tuple[float, float, float]], bevel: float,
          material: bpy.types.Material, target: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def label(name: str, body: str, location: tuple[float, float, float], size: float,
          material: bpy.types.Material, target: bpy.types.Collection,
          rotation: tuple[float, float, float] = (math.pi / 2, 0, 0)) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.size = size
    data.extrude = .015
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    target.objects.link(obj)
    return obj


def camera_and_lights(location: tuple[float, float, float], target: tuple[float, float, float],
                      accent: tuple[float, float, float]) -> None:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("Review Camera")
    cam_data.lens = 48
    cam = bpy.data.objects.new("Review Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    for name, loc, energy, size, color in (
        ("Key", (-10, -12, 19), 1800, 10, (1.0, .78, .55)),
        ("Fill", (14, -3, 12), 1350, 12, accent),
        ("Rim", (2, 15, 16), 1600, 8, (.55, .78, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def scene_settings(resolution_x: int, resolution_y: int, output: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(output)
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.frame_start = 1
    scene.frame_end = 120
    scene.world = bpy.data.worlds.new("Blockout World")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.008, .022, .034, 1)
    background.inputs["Strength"].default_value = .32


def build_loguetown(resolution_x: int, resolution_y: int) -> dict:
    reset()
    topology = collection("00_TOPOLOGY")
    landmarks = collection("10_LANDMARKS")
    states = collection("20_EVENT_STATES")
    atmosphere = collection("30_ATMOSPHERE_FX")
    lod = collection("40_RUNTIME_LOD")
    roger_state = collection("Roger_Execution_CH1", states)
    storm_state = collection("Luffy_Near_Execution_GATE_TBD", states)

    ground = mat("M_Square_Stone", "8b826e", .9)
    street = mat("M_Street", "5d5b54", .94)
    wood = mat("M_Scaffold_Wood", "6c432d", .72)
    wood_light = mat("M_Scaffold_Edges", "c99d5f", .62)
    wall = mat("M_City_Walls", "47616a", .82)
    roof = mat("M_Roofs", "813f38", .78)
    window = mat("M_Window", "d5a84e", .38, emission="ffc85a", emission_strength=1.5)
    silhouette = mat("M_Event_Silhouette", "15191b", .75)
    lightning = mat("M_Lightning", "d6f7ff", .2, emission="d6f7ff", emission_strength=12)
    sign = mat("M_Label", "e8c875", .45, emission="e8c875", emission_strength=.8)

    cube("Central Square", (0, 0, -.25), (10, 8, .25), ground, topology)
    cube("Main Avenue", (0, -5.6, .02), (2.4, 8, .04), street, topology)
    for row, y in enumerate((-6.3, 5.9)):
        for index in range(10):
            x = -9 + index * 2
            height = 2.5 + ((index * 7 + row * 3) % 5) * .42
            cube(f"Building {row + 1}-{index + 1:02d}", (x, y, height / 2), (.78, 1.0, height / 2), wall, landmarks)
            cone(f"Roof {row + 1}-{index + 1:02d}", (x, y, height + .42), 1.08, 0, .85, roof, landmarks, vertices=4).rotation_euler[2] = math.pi / 4
            for level in range(max(1, int(height) - 1)):
                cube(f"Window {row + 1}-{index + 1:02d}-{level + 1}", (x, y - (1.015 if y > 0 else -1.015), .9 + level * .85), (.15, .03, .22), window, landmarks)

    # Four leaning tower legs and cross-bracing make the scaffold an unmistakable 3D landmark.
    feet = ((-1.35, -1.05, 0), (1.35, -1.05, 0), (-1.35, 1.05, 0), (1.35, 1.05, 0))
    tops = ((-.78, -.65, 6.1), (.78, -.65, 6.1), (-.78, .65, 6.1), (.78, .65, 6.1))
    for index, (foot, top) in enumerate(zip(feet, tops)):
        beam(f"Scaffold leg {index + 1}", foot, top, .14, wood_light, landmarks)
    for z in (1.25, 2.55, 3.85, 5.15):
        half_x = 1.35 - z * .09
        half_y = 1.05 - z * .06
        beam(f"Front crossbar {z}", (-half_x, -half_y, z), (half_x, -half_y, z), .11, wood, landmarks)
        beam(f"Back crossbar {z}", (-half_x, half_y, z), (half_x, half_y, z), .11, wood, landmarks)
    beam("Front diagonal A", (-1.28, -1.05, .25), (.82, -.68, 5.9), .09, wood, landmarks)
    beam("Front diagonal B", (1.28, -1.05, .25), (-.82, -.68, 5.9), .09, wood, landmarks)
    cube("Execution deck", (0, 0, 6.18), (1.55, 1.15, .17), wood_light, landmarks)
    cube("Execution backdrop", (0, .92, 6.85), (1.45, .15, .55), wood, landmarks)
    label("Scaffold label", "EXECUTION PLATFORM", (0, .7, 7.7), .42, sign, landmarks, rotation=(math.pi / 2, 0, 0))

    # Chapter-one proxy tableau. It is a state collection, not a permanent landmark occupant.
    cylinder("Roger proxy body", (0, 0, 6.65), .18, .72, silhouette, roger_state, vertices=16)
    sphere("Roger proxy head", (0, 0, 7.08), (.19, .19, .19), silhouette, roger_state)
    for index in range(78):
        x = -8.6 + (index * 2.17) % 17.2
        y = -4.8 + (index * .93) % 8.8
        if abs(x) < 2.0 and abs(y) < 1.8:
            continue
        height = .42 + (index % 4) * .045
        cylinder(f"Crowd proxy {index + 1:02d}", (x, y, height / 2), .09, height, silhouette, roger_state, vertices=10)
        sphere(f"Crowd head {index + 1:02d}", (x, y, height + .10), (.105, .105, .105), silhouette, roger_state)

    # Later scene stays in-file but off by default until its chapter is verified.
    bolt = [(-3, 2, 11), (-1.5, 1, 9.5), (-2.1, .3, 8.4), (-.3, -.2, 7.1), (0, 0, 6.4)]
    curve("Storm lightning gate TBD", bolt, .07, lightning, storm_state)
    storm_state.hide_render = True
    storm_state.hide_viewport = True
    for index in range(60):
        x = -10 + (index * 3.41) % 20
        y = -8 + (index * 1.87) % 16
        curve(f"Rain streak {index + 1:02d}", [(x, y, 10), (x - .18, y, 8.8)], .012, lightning, atmosphere)
    atmosphere.hide_render = True
    atmosphere.hide_viewport = True
    lod["purpose"] = "future runtime simplification; empty in blockout"

    output = RENDERS / "loguetown-roger-execution.png"
    scene_settings(resolution_x, resolution_y, output)
    camera_and_lights((15.8, -20.5, 11.8), (0, 0, 3.1), (.50, .74, .86))
    bpy.context.scene.frame_set(1)
    blend = SOURCE / "loguetown-roger-execution.blend"
    bpy.context.scene["contract"] = "contracts/loguetown-roger-execution.visual.json"
    bpy.context.scene["maturity"] = "3d_blockout_not_final_art"
    bpy.context.scene["event_state"] = "Roger_Execution_CH1"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)
    return {"id": "loguetown-roger-execution", "blend": blend, "render": output, "frame_end": 120,
            "collections": [topology.name, landmarks.name, states.name, atmosphere.name, lod.name]}


def build_water7(resolution_x: int, resolution_y: int) -> dict:
    reset()
    topology = collection("00_TOPOLOGY")
    landmarks = collection("10_LANDMARKS")
    states = collection("20_EVENT_STATES")
    atmosphere = collection("30_ATMOSPHERE_FX")
    lod = collection("40_RUNTIME_LOD")
    normal_state = collection("Puffing_Tom_Network_CH322", states)
    storm_state = collection("Rocketman_Aqua_Laguna_GATE_TBD", states)
    post_state = collection("Puffing_Ice_CH656", states)

    sea = mat("M_Ocean", "0d5268", .28, metallic=.08)
    rail = mat("M_Subsurface_Rail", "89dce4", .25, metallic=.65, emission="52dbea", emission_strength=1.1)
    island = mat("M_Island", "747b57", .83)
    stone = mat("M_Water7_Stone", "d0b98f", .75)
    roof = mat("M_Water7_Roofs", "a95142", .68)
    station_mat = mat("M_Station", "d9cfb5", .73)
    government = mat("M_Enies", "e1dfcf", .7)
    train_dark = mat("M_Train_Dark", "272d2e", .42, metallic=.18)
    train_gold = mat("M_Train_Trim", "e1bd6c", .38, metallic=.45)
    wheel = mat("M_Wheel", "8d4e2d", .4, metallic=.25)
    label_mat = mat("M_Labels", "e7f9f5", .42, emission="b6ffff", emission_strength=.7)
    storm = mat("M_Storm", "8fa9c8", .32, emission="a4d1ff", emission_strength=2.2)
    rocket_red = mat("M_Rocketman_Red", "b53e32", .46, metallic=.16)

    cube("Ocean surface", (0, 0, -.55), (18, 12, .5), sea, topology)
    nodes = {
        "Water 7": (-10.5, -1.0, 3.3),
        "Enies Lobby": (11.2, 1.0, 3.1),
        "Pucci": (-2.7, 6.0, 1.55),
        "St. Poplar": (2.2, 7.4, 1.55),
        "San Faldo": (6.8, 5.5, 1.55),
        "Shift Station": (-.5, -4.2, 1.0),
    }

    # Every curve carries an explicit warning: this relationship graph is not canon bearing data.
    main_points = [(-8.5, -1, .06), (-4.2, -2.2, .04), (1.5, -2.6, .03), (6.4, -.8, .04), (9.1, .8, .06)]
    routes = {
        "Water7 to Enies": main_points,
        "Water7 to Pucci": [(-9, -.2, .06), (-7, 3.4, .04), (-3.8, 5.6, .05)],
        "Water7 to StPoplar": [(-9, 0, .06), (-5.5, 4.5, .04), (1.2, 7.0, .05)],
        "Water7 to SanFaldo": [(-9, .1, .06), (-4.0, 3.3, .04), (5.7, 5.2, .05)],
    }
    for name, points in routes.items():
        for side in (-.13, .13):
            shifted = [(x, y + side, z) for x, y, z in points]
            obj = curve(f"Schematic rail {name} {side:+.2f}", shifted, .065, rail, topology)
            obj["coordinate_status"] = "relationship_schematic_not_canon_bearing"

    # Water 7 reads as a tiered water-city mass rather than a flat island disc.
    x, y, _ = nodes["Water 7"]
    cylinder("Water 7 base", (x, y, .28), 3.3, .55, island, landmarks, vertices=64)
    for level in range(5):
        radius = 2.75 - level * .42
        z = .62 + level * .73
        cylinder(f"Water 7 tier {level + 1}", (x, y, z), radius, .55, stone, landmarks, vertices=48)
        for building_index in range(12 - level):
            angle = math.tau * building_index / (12 - level) + level * .21
            bx = x + math.cos(angle) * radius * .72
            by = y + math.sin(angle) * radius * .72
            cube(f"Water7 house {level + 1}-{building_index + 1}", (bx, by, z + .48), (.17, .17, .35), roof, landmarks)
    cylinder("Water 7 fountain crown", (x, y, 4.3), .58, 1.3, stone, landmarks, vertices=32)
    label("Water 7 label", "WATER 7", (x, y - 3.65, .45), .46, label_mat, landmarks)

    # Enies Lobby blockout includes the waterfall void and terminus platform.
    ex, ey, _ = nodes["Enies Lobby"]
    bpy.ops.mesh.primitive_torus_add(major_radius=2.25, minor_radius=.58, major_segments=64, minor_segments=16,
                                     location=(ex, ey, .35))
    ring = bpy.context.object
    ring.name = "Enies waterfall ring"
    ring.data.materials.append(government)
    move(ring, landmarks)
    cube("Enies court platform", (ex, ey, .85), (1.45, 1.15, .32), government, landmarks)
    cube("Enies courthouse", (ex, ey + .2, 2.0), (.75, .7, .9), government, landmarks)
    tag_runtime(
        cube("Day Station", (ex - 2.55, ey - 1.4, .48), (.65, .42, .42), station_mat, landmarks),
        "day-station", confidence="chapter_to_verify", default_hidden=True,
    )
    label("Enies label", "ENIES LOBBY", (ex, ey - 3.35, .45), .4, label_mat, landmarks)

    colors = (island, stone, roof)
    for node_index, node_name in enumerate(("Pucci", "St. Poplar", "San Faldo")):
        nx, ny, _ = nodes[node_name]
        cylinder(f"{node_name} island", (nx, ny, .18), 1.55, .38, colors[node_index], landmarks, vertices=40)
        cube(f"{node_name} station", (nx, ny - 1.15, .55), (.48, .32, .38), station_mat, landmarks)
        label(f"{node_name} label", node_name.upper(), (nx, ny, .52), .28, label_mat, landmarks)
    sx, sy, _ = nodes["Shift Station"]
    cylinder("Shift Station rock", (sx, sy, .16), 1.0, .34, island, landmarks, vertices=32)
    cube("Shift Station building", (sx, sy, .65), (.58, .46, .5), station_mat, landmarks)
    cylinder("Shift Station lighthouse", (sx + .45, sy + .1, 1.25), .16, 1.6, government, landmarks, vertices=20)
    label("Shift Station label", "SHIFT STATION", (sx, sy - 1.2, .42), .25, label_mat, landmarks)

    # Puffing Tom is an editable proxy with a real 120-frame route animation.
    train = collection("Puffing_Tom_Train", normal_state)
    engine = cube("Puffing Tom engine", main_points[0], (1.0, .58, .6), train_dark, train)
    cube("Puffing Tom cab", (main_points[0][0] - .1, main_points[0][1], .9), (.48, .48, .52), train_dark, train)
    cylinder("Puffing Tom stack", (main_points[0][0] + .45, main_points[0][1], 1.27), .18, .85, train_dark, train, vertices=24)
    for side in (-.62, .62):
        for offset in (-.55, .45):
            wheel_obj = cylinder(f"Puffing Tom wheel {side} {offset}", (main_points[0][0] + offset, main_points[0][1] + side, .18), .31, .16, wheel, train, vertices=24)
            wheel_obj.rotation_euler[0] = math.pi / 2
    cube("Puffing Tom trim", (main_points[0][0], main_points[0][1] - .61, .55), (1.05, .04, .08), train_gold, train)
    for obj in train.objects:
        obj["preview_vehicle"] = True
        base = obj.location.copy()
        for frame, coordinate in ((1, main_points[0]), (42, main_points[1]), (72, main_points[2]), (96, main_points[3]), (120, main_points[4])):
            delta = Vector(coordinate) - Vector(main_points[0])
            obj.location = base + delta
            obj.keyframe_insert(data_path="location", frame=frame)
    bpy.context.scene.frame_set(70)

    # Gated variants are stored but not shown in the default chapter-322 blockout.
    # They remain in the GLB with explicit default-hidden node extras.
    rocket_origin = (-7.4, -1.45, .58)
    rocket_parts = [
        cube("Rocketman engine", rocket_origin, (.88, .52, .54), rocket_red, storm_state),
        cube("Rocketman cab", (-7.72, -1.45, 1.08), (.42, .44, .48), train_dark, storm_state),
        cylinder("Rocketman stack", (-7.03, -1.45, 1.28), .16, .72, train_dark, storm_state, vertices=20),
        cube("Rocketman trim", (-7.4, -1.98, .55), (.92, .04, .08), train_gold, storm_state),
    ]
    for side in (-.56, .56):
        for offset in (-.48, .42):
            wheel_obj = cylinder(
                f"Rocketman wheel {side} {offset}",
                (rocket_origin[0] + offset, rocket_origin[1] + side, .2),
                .28, .14, wheel, storm_state, vertices=20,
            )
            wheel_obj.rotation_euler[0] = math.pi / 2
            rocket_parts.append(wheel_obj)
    for obj in rocket_parts:
        tag_runtime(obj, "rocketman", confidence="chapter_to_verify", default_hidden=True)

    tag_runtime(
        curve("Aqua Laguna wave wall", [(-14, 9, 2), (-4, 8, 5.5), (6, 9, 3.5), (15, 8, 6)],
              .7, storm, storm_state),
        "aqua-laguna", confidence="chapter_to_verify", default_hidden=True,
    )
    storm_state.hide_render = True
    storm_state.hide_viewport = True
    post_state.hide_render = True
    post_state.hide_viewport = True
    post_state["reveal_chapter"] = 656
    atmosphere["normal_fx"] = "wheel spray, paddle wake, steam; deferred after blockout"
    lod["purpose"] = "future simplified rail, station, and vehicle exports"

    output = RENDERS / "water-7-sea-train-network.png"
    scene_settings(resolution_x, resolution_y, output)
    camera_and_lights((21, -26, 22), (0, 1, 1.2), (.35, .78, .88))
    bpy.context.scene.frame_set(70)
    blend = SOURCE / "water-7-sea-train-network.blend"
    bpy.context.scene["contract"] = "contracts/water-7-sea-train-network.visual.json"
    bpy.context.scene["maturity"] = "3d_blockout_not_final_art"
    bpy.context.scene["coordinate_status"] = "route_bearings_schematic_not_canon"
    bpy.context.scene["animation"] = "Puffing Tom frame 1-120"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    fallback_hidden = [
        obj for obj in bpy.context.scene.objects
        if bool(obj.get("default_hidden", False))
    ]
    for obj in fallback_hidden:
        obj.hide_render = True
    bpy.ops.render.render(write_still=True)
    for obj in fallback_hidden:
        obj.hide_render = False
    return {"id": "water-7-sea-train-network", "blend": blend, "render": output, "frame_end": 120,
            "collections": [topology.name, landmarks.name, states.name, atmosphere.name, lod.name]}


def main() -> int:
    options = args()
    selected = options.only or list(ASSETS)
    SOURCE.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    results = []
    builders = {
        "loguetown-roger-execution": build_loguetown,
        "water-7-sea-train-network": build_water7,
    }
    for asset_id in selected:
        result = builders[asset_id](options.resolution_x, options.resolution_y)
        result.update({
            "contract": f"contracts/{asset_id}.visual.json",
            "contract_sha256": sha(CONTRACTS / f"{asset_id}.visual.json"),
            "blend": str(result["blend"].relative_to(ROOT)),
            "render": str(result["render"].relative_to(ROOT)),
            "maturity": "3d_blockout_not_final_art",
            "runtime_export": False,
        })
        result["blend_sha256"] = sha(ROOT / result["blend"])
        result["render_sha256"] = sha(ROOT / result["render"])
        results.append(result)
        print(f"built {asset_id}")
    existing = {"schema_version": 1, "generator": "scripts/build_priority_narrative_blockouts.py", "assets": []}
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in existing.get("assets", [])}
    by_id.update({item["id"]: item for item in results})
    existing["assets"] = [by_id[key] for key in sorted(by_id)]
    MANIFEST.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
