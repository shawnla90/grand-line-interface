#!/usr/bin/env python3
"""Build chapter-driven geographic systems for Water 7 and the Red Line.

These are local explanatory theatres, not canon survey maps.  The stable atlas
anchor opens the scene; component extras and named actions let the web runtime
sample the correct chapter state without baking spoilers into the globe.

Run with Blender 4.5+:
  Blender --background --python scripts/build_dynamic_geography_systems.py -- \
    --only water-7-sea-train-network
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_runtime_scene_batch as core  # noqa: E402


ASSETS = (
    "water-7-sea-train-network",
    "mary-geoise-red-line",
    "fish-man-red-line-descent",
)


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=ASSETS)
    parser.add_argument("--resolution-x", type=int, default=1400)
    parser.add_argument("--resolution-y", type=int, default=1000)
    return parser.parse_args(argv)


def parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world


def tag_many(
    objects: list[bpy.types.Object],
    component: str,
    reveal: int | None,
    *,
    confidence: str = "verified",
    default_hidden: bool = False,
    active_through: float | None = None,
) -> list[bpy.types.Object]:
    for obj in objects:
        core.tag(
            obj,
            component,
            reveal,
            confidence=confidence,
            default_hidden=default_hidden,
        )
        if active_through is not None:
            obj["active_through_chapter"] = active_through
    return objects


def state_tag(
    objects: list[bpy.types.Object], component: str, reveal: int, active_through: float
) -> list[bpy.types.Object]:
    return tag_many(
        objects,
        component,
        reveal,
        confidence="verified_state_window",
        default_hidden=True,
        active_through=active_through,
    )


def set_linear_action(obj: bpy.types.Object, name: str) -> None:
    if not obj.animation_data or not obj.animation_data.action:
        raise RuntimeError(f"{obj.name} has no action")
    obj.animation_data.action.name = name
    for fcurve in obj.animation_data.action.fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "LINEAR"


def animate_location(
    obj: bpy.types.Object,
    name: str,
    keys: list[tuple[int, tuple[float, float, float]]],
) -> None:
    for frame, location in keys:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    set_linear_action(obj, name)


def animate_scale(
    obj: bpy.types.Object,
    name: str,
    keys: list[tuple[int, tuple[float, float, float]]],
) -> None:
    for frame, scale in keys:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)
    set_linear_action(obj, name)


def make_rock_slab(
    name: str,
    z: float,
    height: float,
    radius_x: float,
    radius_y: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    phase: float = 0.0,
    vertices: int = 18,
) -> bpy.types.Object:
    """Create a deterministic irregular prism for a non-boxy rock silhouette."""
    coords: list[tuple[float, float, float]] = []
    for level_z in (z - height / 2, z + height / 2):
        for i in range(vertices):
            a = math.tau * i / vertices
            wobble = 1 + .10 * math.sin(a * 3 + phase) + .055 * math.sin(a * 7 - phase)
            coords.append((math.cos(a) * radius_x * wobble, math.sin(a) * radius_y * wobble, level_z))
    faces: list[tuple[int, ...]] = []
    faces.append(tuple(range(vertices - 1, -1, -1)))
    faces.append(tuple(range(vertices, vertices * 2)))
    for i in range(vertices):
        nxt = (i + 1) % vertices
        faces.append((i, nxt, vertices + nxt, vertices + i))
    mesh = bpy.data.meshes.new(f"{name} Mesh")
    mesh.from_pydata(coords, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    return obj


def train(
    prefix: str,
    origin: tuple[float, float, float],
    body_mat: bpy.types.Material,
    trim_mat: bpy.types.Material,
    wheel_mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    cars: int = 2,
) -> list[bpy.types.Object]:
    x, y, z = origin
    parts: list[bpy.types.Object] = []
    root = core.cube(f"{prefix} engine root", origin, (.82, .44, .43), body_mat, target)
    parts.append(root)
    parts.append(core.cube(f"{prefix} cab", (x - .2, y, z + .52), (.42, .37, .38), body_mat, target))
    parts.append(core.cylinder(f"{prefix} stack", (x + .38, y, z + .68), .13, .66, body_mat, target, 18))
    parts.append(core.cone(f"{prefix} stack cap", (x + .38, y, z + 1.04), .22, .12, .16, trim_mat, target, 18))
    parts.append(core.cube(f"{prefix} gold rail", (x, y - .46, z), (.86, .035, .07), trim_mat, target))
    for car in range(cars):
        cx = x - 1.42 - car * 1.36
        parts.append(core.cube(f"{prefix} passenger car {car+1}", (cx, y, z + .06), (.58, .41, .38), body_mat, target))
        parts.append(core.cube(f"{prefix} passenger roof {car+1}", (cx, y, z + .48), (.62, .44, .08), trim_mat, target))
    wheel_x = [x - 1.42 - car * 1.36 + off for car in range(cars) for off in (-.34, .34)] + [x - .48, x + .48]
    for side in (-.45, .45):
        for index, wx in enumerate(wheel_x):
            obj = core.cylinder(f"{prefix} wheel {side:+}-{index+1}", (wx, y + side, z - .34), .22, .12, wheel_mat, target, 16)
            obj.rotation_euler[0] = math.pi / 2
            parts.append(obj)
    for obj in parts[1:]:
        parent_keep_world(obj, root)
    return parts


def build_water7(contract: dict, rx: int, ry: int) -> dict:
    core.reset()
    c = core.collections()
    sea = core.material("M_W7_Sea", "0b4965", .22, emission="0c526d", emission_strength=.25)
    rail = core.material("M_W7_Rail", "7ddce7", .25, metallic=.65, emission="4ccce0", emission_strength=1.0)
    stone = core.material("M_W7_Stone", "d5c39d", .74)
    stone_dark = core.material("M_W7_Stone_Dark", "937d60", .86)
    roof = core.material("M_W7_Roof", "b34d3d", .66)
    canal = core.material("M_W7_Canal", "2d9bb4", .18, emission="45bfd0", emission_strength=.5)
    brass = core.material("M_Train_Brass", "e4bd61", .33, metallic=.48)
    train_dark = core.material("M_Train_Dark", "222c35", .38, metallic=.25)
    rocket_red = core.material("M_Rocketman_Red", "b83c31", .45, metallic=.16)
    ice_white = core.material("M_Puffing_Ice", "e8f6f8", .4, metallic=.2)
    wheel = core.material("M_Train_Wheel", "6c3b2c", .42, metallic=.3)
    justice = core.material("M_Enies_Justice", "e8e0c9", .7)
    justice_blue = core.material("M_Enies_Roof", "5e84a2", .62)
    abyss = core.material("M_Enies_Abyss", "050912", .92, emission="07101d", emission_strength=.2)
    fall = core.material("M_Enies_Waterfall", "a8ebf3", .18, emission="69d3e2", emission_strength=1.0, alpha=.72)
    daylight = core.material("M_Enies_Daylight", "fff0ad", .3, emission="ffe38d", emission_strength=2.2)
    storm = core.material("M_Aqua_Laguna", "80bcd0", .24, emission="67b4ce", emission_strength=.7, alpha=.78)
    storm_dark = core.material("M_Aqua_Storm", "607b99", .4, emission="7b9fbe", emission_strength=.3, alpha=.72)

    tag_many([core.cube("Sea Train ocean stage", (0, 0, -.62), (17.8, 11.5, .5), sea, c.topology)], "subsurface-sea-rails", 322)

    water7 = (-10.0, -1.3)
    enies = (10.3, 1.0)
    routes = {
        "Water 7 to Enies": [(-8.1, -1.3, .08), (-4.2, -2.0, .06), (1.0, -2.25, .05), (5.8, -.8, .06), (8.3, .55, .08)],
        "Water 7 to Pucci": [(-8.2, -.6, .08), (-6.8, 3.2, .06), (-3.3, 6.1, .08)],
        "Water 7 to St Poplar": [(-8.1, -.45, .08), (-4.5, 4.4, .06), (1.6, 7.2, .08)],
        "Water 7 to San Faldo": [(-8.0, -.3, .08), (-2.6, 3.1, .06), (6.3, 5.6, .08)],
    }
    for name, points in routes.items():
        for side in (-.13, .13):
            obj = core.curve(f"Subsurface rail {name} {side:+.2f}", [(x, y + side, z) for x, y, z in points], .06, rail, c.topology)
            obj["coordinate_status"] = "relationship_schematic_not_canon_bearing"
            tag_many([obj], "subsurface-sea-rails", 322)

    # Water 7: terraced seawalls, circular canals, radial waterways and dense city fabric.
    w7_parts: list[bpy.types.Object] = []
    for level in range(6):
        radius = 3.45 - level * .43
        z = .18 + level * .67
        w7_parts.append(core.cylinder(f"Water 7 seawall tier {level+1}", (water7[0], water7[1], z), radius, .46, stone_dark if level < 2 else stone, c.topology, 56))
        if level < 5:
            w7_parts.append(core.torus(f"Water 7 canal ring {level+1}", (water7[0], water7[1], z + .27), radius - .22, .10, canal, c.landmarks))
        count = max(8, 18 - level * 2)
        for i in range(count):
            a = math.tau * i / count + level * .18
            r = radius * .72
            bx, by = water7[0] + math.cos(a) * r, water7[1] + math.sin(a) * r
            before = set(bpy.context.scene.objects)
            core.house(f"Water 7 district {level+1}-{i+1:02d}", (bx, by, z + .28), .43 + .04 * (i % 3), stone, roof, c.landmarks)
            w7_parts.extend([obj for obj in bpy.context.scene.objects if obj not in before])
    for i in range(10):
        a = math.tau * i / 10
        w7_parts.append(core.curve(f"Water 7 radial canal {i+1}", [(water7[0], water7[1], 4.2), (water7[0] + math.cos(a) * 1.8, water7[1] + math.sin(a) * 1.8, 2.45), (water7[0] + math.cos(a) * 3.3, water7[1] + math.sin(a) * 3.3, .55)], .11, canal, c.landmarks))
    w7_parts.extend([
        core.cylinder("Water 7 fountain crown", (water7[0], water7[1], 4.68), .62, 1.45, stone, c.landmarks, 28),
        core.torus("Water 7 crown fountain rim", (water7[0], water7[1], 5.38), .78, .10, canal, c.landmarks),
        core.cube("Blue Station", (-7.75, -2.6, .48), (.85, .55, .42), stone, c.landmarks),
    ])
    tag_many(w7_parts, "water-7", 323)
    tag_many([w7_parts[-1]], "blue-station", 322)

    # Connected route nodes remain explicitly schematic.
    for cid, label, loc, reveal, color in (
        ("pucci", "Pucci", (-3.3, 6.25), 657, roof),
        ("st-poplar", "St. Poplar", (1.6, 7.35), 496, stone),
        ("san-faldo", "San Faldo", (6.3, 5.75), 322, roof),
    ):
        parts = [core.island(f"{label} island", (loc[0], loc[1], .18), 1.18, .38, color, c.landmarks, (1.0, .78), 30),
                 core.cube(f"{label} station", (loc[0], loc[1] - .75, .55), (.38, .28, .34), stone, c.landmarks)]
        tag_many(parts, cid, reveal)
    shift_parts = [core.island("Shift Station rock", (-.5, -5.0, .16), 1.0, .34, stone_dark, c.landmarks, (1, .8), 30),
                   core.cube("Shift Station building", (-.5, -5.0, .67), (.52, .42, .5), stone, c.landmarks),
                   core.cylinder("Shift Station lighthouse", (.0, -4.92, 1.3), .14, 1.55, justice, c.landmarks, 16)]
    tag_many(shift_parts, "shift-station", 322)

    # Enies Lobby is a never-night court island above a permanent abyss and waterfall ring.
    enies_parts = [
        core.cylinder("Enies Lobby black ocean void", (enies[0], enies[1], -.05), 3.0, .18, abyss, c.topology, 64),
        core.torus("Enies Lobby stone rim", (enies[0], enies[1], .18), 2.7, .42, justice, c.landmarks),
        core.island("Enies Lobby court island", (enies[0], enies[1], 1.0), 1.72, .65, justice, c.landmarks, (1.0, .78), 40),
        core.cube("Enies Lobby courthouse", (enies[0], enies[1] + .15, 2.05), (.82, .68, .92), justice, c.landmarks),
        core.cube("Tower of Justice", (enies[0] + 1.55, enies[1] + .25, 2.25), (.55, .5, 1.15), justice, c.landmarks),
        core.curve("Enies Lobby land bridge", [(7.7, -1.1, .55), (8.6, -.2, .75), (9.0, .55, 1.0)], .32, justice, c.landmarks),
        core.sphere("Enies Lobby never-night light", (enies[0] - 1.8, enies[1] + 1.6, 5.0), (.55, .55, .55), daylight, c.atmosphere, 20, 10),
    ]
    for x in (-.5, .5):
        enies_parts.append(core.cylinder(f"Enies front gate tower {x:+}", (8.2 + x, -.95, 1.45), .24, 2.2, justice, c.landmarks, 14))
        enies_parts.append(core.cone(f"Enies front gate roof {x:+}", (8.2 + x, -.95, 2.65), .38, 0, .5, justice_blue, c.landmarks, 14))
    tag_many(enies_parts, "enies-lobby", 358)
    day = [core.cube("Day Station", (7.7, -1.55, .55), (.68, .45, .42), stone, c.landmarks),
           core.cube("Day Station platform", (7.45, -1.55, .25), (1.2, .62, .12), justice, c.landmarks)]
    tag_many(day, "day-station", 375)

    waterfall_parts: list[bpy.types.Object] = []
    root = core.torus("Enies waterfall animated root", (enies[0], enies[1], .05), 2.52, .18, fall, c.atmosphere)
    waterfall_parts.append(root)
    for i in range(28):
        a = math.tau * i / 28
        x, y = enies[0] + math.cos(a) * 2.52, enies[1] + math.sin(a) * 2.52
        # Lift the curtain through the local ocean plane so the permanent fall
        # reads in an oblique map camera instead of disappearing below the stage.
        curtain = core.cube(f"Enies waterfall curtain {i+1:02d}", (x, y, .12), (.16, .16, .68), fall, c.atmosphere)
        parent_keep_world(curtain, root)
        waterfall_parts.append(curtain)
    tag_many(waterfall_parts, "enies-lobby", 358)
    animate_scale(root, "water7_enies_waterfall_cycle", [(1, (1, 1, 1)), (51, (1.025, 1.025, .93)), (101, (1, 1, 1))])

    puff = train("Puffing Tom", routes["Water 7 to Enies"][0], train_dark, brass, wheel, c.states, cars=3)
    tag_many(puff, "puffing-tom", 322)
    animate_location(puff[0], "water7_puffing_tom_route_cycle", [
        (1, routes["Water 7 to Enies"][0]),
        (31, routes["Water 7 to Enies"][1]),
        (61, routes["Water 7 to Enies"][2]),
        (91, routes["Water 7 to Enies"][3]),
        (121, routes["Water 7 to Enies"][0]),
    ])

    rocket = train("Rocketman", (-8.0, -1.8, .54), rocket_red, brass, wheel, c.states, cars=1)
    state_tag(rocket, "rocketman", 365, 378.999)
    animate_location(rocket[0], "water7_rocketman_route_state", [
        (1, (-8.0, -1.8, .54)),
        (25, (-4.8, -2.25, .56)),
        (61, (1.0, -2.55, .55)),
        (99, (6.0, -.85, .57)),
        (121, (8.2, .45, .58)),
    ])

    wave_parts: list[bpy.types.Object] = []
    wave_root = core.cube("Aqua Laguna tide root", (water7[0], water7[1] + 4.3, .35), (3.9, .26, .32), storm, c.states)
    wave_parts.append(wave_root)
    for i in range(18):
        x = water7[0] - 4.0 + i * .47
        crest = core.sphere(f"Aqua Laguna crest {i+1:02d}", (x, water7[1] + 4.2 + .15 * math.sin(i), .7 + .18 * (i % 3)), (.42, .34, .48), storm, c.states, 12, 7)
        parent_keep_world(crest, wave_root)
        wave_parts.append(crest)
    for i in range(12):
        cloud = core.sphere(f"Aqua Laguna storm cloud {i+1:02d}", (water7[0] - 4.2 + i * .75, water7[1] + 3.5, 5.7 + .25 * (i % 3)), (.95, .68, .42), storm_dark, c.states, 12, 7)
        parent_keep_world(cloud, wave_root)
        wave_parts.append(cloud)
    state_tag(wave_parts, "aqua-laguna", 363, 367.999)
    animate_scale(wave_root, "water7_aqua_laguna_tide_state", [
        (1, (1, 1, .18)),
        (25, (1.02, 1, .6)),
        (50, (1.06, 1, 1.0)),
        (76, (1.08, 1, 1.28)),
        (101, (1.04, 1, .9)),
        (121, (1, 1, .45)),
    ])

    puff_ice = train("Puffing Ice", (-2.6, 5.6, .54), ice_white, brass, wheel, c.states, cars=2)
    tag_many(puff_ice, "puffing-ice", 656)
    bpy.context.scene.frame_end = 121
    result = core.finish(
        "water-7-sea-train-network", contract, c, rx, ry,
        (23, -29, 22), (0, .5, 1.25), safe_full_chapter=657,
        layout_status="dynamic_relationship_graph_not_canon_bearings",
    )
    bpy.context.scene.frame_end = 121
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "source/water-7-sea-train-network.blend"))
    return result


def build_mary_geoise(contract: dict, rx: int, ry: int) -> dict:
    core.reset()
    c = core.collections()
    red = core.material("M_Red_Line_Rock", "7b392f", .94)
    red_light = core.material("M_Red_Line_Strata", "a35943", .88)
    summit = core.material("M_Mary_Stone", "ddd5c6", .74)
    roof = core.material("M_Pangaea_Roof", "58758e", .62)
    gold = core.material("M_Bondola_Gold", "e0bb55", .36, metallic=.5)
    cabin = core.material("M_Bondola_Cabin", "a64437", .52, metallic=.12)
    sea = core.material("M_Red_Port_Sea", "0a405b", .22, emission="0c516c", emission_strength=.25)
    cloud = core.material("M_Red_Line_Cloud", "dce9ed", .6, emission="bfe3ea", emission_strength=.32, alpha=.58)
    green = core.material("M_Mary_Garden", "447653", .8)

    cliff_parts: list[bpy.types.Object] = []
    for level in range(7):
        z = .8 + level * 1.55
        cliff_parts.append(make_rock_slab(
            f"Red Line irregular stratum {level+1}", z, 1.7,
            5.45 - .10 * level + .18 * math.sin(level),
            3.15 - .05 * level + .16 * math.cos(level * 1.3),
            red_light if level % 3 == 1 else red, c.topology, phase=level * .73,
        ))
    tag_many(cliff_parts, "red-line-summit", 142)

    summit_parts = [make_rock_slab("Mary Geoise summit plateau", 11.35, .55, 5.75, 3.45, summit, c.landmarks, phase=1.4, vertices=24)]
    for side, y in enumerate((-2.45, 2.45)):
        for i in range(10):
            before = set(bpy.context.scene.objects)
            core.house(f"Mary Geoise district {side+1}-{i+1:02d}", (-4.25 + i * .95, y, 11.62), .45, summit, roof, c.landmarks)
            summit_parts.extend([obj for obj in bpy.context.scene.objects if obj not in before])
    summit_parts.extend([
        core.cube("Mary Geoise processional avenue", (0, -1.1, 11.72), (.48, 2.0, .12), summit, c.landmarks),
        core.cylinder("Mary Geoise garden", (-2.7, .1, 11.78), 1.05, .18, green, c.landmarks, 32, scale_xy=(1, .65)),
    ])
    tag_many(summit_parts, "mary-geoise", 142)

    castle: list[bpy.types.Object] = [core.cube("Pangaea Castle central keep", (0, .35, 12.95), (1.55, 1.15, 1.3), summit, c.landmarks)]
    for x in (-1.45, -.55, .55, 1.45):
        castle.append(core.cylinder(f"Pangaea Castle tower {x:+}", (x, .3, 13.55), .38, 2.5, summit, c.landmarks, 16))
        castle.append(core.cone(f"Pangaea Castle roof {x:+}", (x, .3, 14.95), .52, 0, .55, roof, c.landmarks, 16))
    castle.append(core.cube("Pangaea Castle gate", (0, -1.0, 12.35), (.55, .18, .62), roof, c.landmarks))
    tag_many(castle, "pangaea-castle", 142)

    paradise_port = [
        core.island("Paradise Red Port harbor", (0, -5.65, .0), 4.6, .25, sea, c.topology, (1, .42), 44),
        core.cube("Paradise Red Port quay", (0, -5.1, .42), (2.3, .62, .38), summit, c.landmarks),
        core.cube("Paradise Red Port terminal", (0, -4.9, 1.05), (1.2, .54, .52), summit, c.landmarks),
    ]
    for x in (-1.65, 1.65):
        paradise_port.append(core.cylinder(f"Paradise Red Port beacon {x:+}", (x, -5.3, 1.0), .16, 1.5, summit, c.landmarks, 14))
    tag_many(paradise_port, "red-port-paradise", 905)

    # The opposite port remains authored but spoiler-locked until its independent gate is verified.
    new_world_port = [
        core.island("New World Red Port water", (0, 5.65, .0), 4.6, .25, sea, c.topology, (1, .42), 44),
        core.cube("New World Red Port quay", (0, 5.1, .42), (2.3, .62, .38), summit, c.landmarks),
    ]
    tag_many(new_world_port, "red-port-new-world", None, confidence="chapter_to_verify", default_hidden=True)

    cables: list[bpy.types.Object] = []
    for x in (-.72, .72):
        cables.append(core.curve(f"Paradise Bondola cable {x:+}", [(x, -4.7, 1.0), (x, -3.5, 4.2), (x, -2.1, 8.0), (x, -.8, 11.2)], .055, gold, c.landmarks))
    tag_many(cables, "bondola-route", 905)

    bondola: list[bpy.types.Object] = [core.cube("Bondola ascent cabin root", (0, -4.35, 1.35), (.58, .38, .42), cabin, c.states)]
    bondola.extend([
        core.cube("Bondola cabin deck", (0, -4.35, .98), (.72, .5, .08), gold, c.states),
        core.cube("Bondola canopy", (0, -4.35, 1.86), (.66, .46, .09), gold, c.states),
    ])
    for x in (-.52, .52):
        bondola.append(core.beam(f"Bondola suspension {x:+}", (x, -4.35, 1.05), (x, -4.35, 2.25), .035, gold, c.states))
    for obj in bondola[1:]:
        parent_keep_world(obj, bondola[0])
    tag_many(bondola, "bondola-route", 905)
    animate_location(bondola[0], "mary_geoise_bondola_cycle", [
        (1, (0, -4.35, 1.35)), (41, (0, -3.0, 5.0)), (81, (0, -1.7, 8.8)), (121, (0, -.75, 11.35)),
    ])

    cloud_parts: list[bpy.types.Object] = []
    cloud_root = core.sphere("Red Line cloud drift root", (-5.8, -1.0, 10.2), (1.25, .72, .46), cloud, c.atmosphere, 14, 8)
    cloud_parts.append(cloud_root)
    for i in range(14):
        a = math.tau * i / 14
        puff = core.sphere(f"Red Line cloud bank {i+1:02d}", (math.cos(a) * 6.1, -1.0 + math.sin(a) * 2.4, 9.7 + .25 * (i % 3)), (1.25, .7, .42), cloud, c.atmosphere, 14, 8)
        parent_keep_world(puff, cloud_root)
        cloud_parts.append(puff)
    tag_many(cloud_parts, "red-line-summit", 142)
    animate_location(cloud_root, "red_line_cloud_drift", [(1, (-5.8, -1.0, 10.2)), (61, (5.8, -1.0, 10.2)), (121, (-5.8, -1.0, 10.2))])

    result = core.finish(
        "mary-geoise-red-line", contract, c, rx, ry,
        (20, -27, 18), (0, 0, 7.0), safe_full_chapter=905,
        layout_status="vertical_cross_section_with_irregular_stylized_coastline",
    )
    bpy.context.scene.frame_end = 121
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "source/mary-geoise-red-line.blend"))
    return result


def build_fishman_descent(contract: dict, rx: int, ry: int) -> dict:
    core.reset()
    c = core.collections()
    surface = core.material("M_Descent_Surface", "1d7895", .2, emission="2b99b2", emission_strength=.5, alpha=.82)
    midwater = core.material("M_Descent_Midwater", "123f69", .34, emission="164d75", emission_strength=.35, alpha=.5)
    deep = core.material("M_Descent_Deep", "071727", .55, emission="0b2137", emission_strength=.25)
    red = core.material("M_Descent_Red_Line", "6f352f", .94)
    strata = core.material("M_Descent_Strata", "984a3e", .86)
    resin = core.material("M_Coating_Resin", "9cecf1", .12, emission="64dbe5", emission_strength=1.0, alpha=.25)
    ship = core.material("M_Sunny_Hull", "8d4b2c", .65)
    sunny = core.material("M_Sunny_Gold", "e3bd4c", .36, metallic=.2)
    sail = core.material("M_Sunny_Sail", "f2e2c2", .62)
    current = core.material("M_Descent_Current", "72d7e4", .2, emission="52c9db", emission_strength=1.4, alpha=.7)
    creature = core.material("M_Deep_Creature", "24425b", .78, emission="356d82", emission_strength=.3)
    kraken_mat = core.material("M_Kraken", "75416e", .62, emission="9d5292", emission_strength=.25)
    lava = core.material("M_Deep_Lava", "de552f", .35, emission="ff6335", emission_strength=2.5)
    gate = core.material("M_Fishman_Gate", "8ee5d5", .2, emission="78efd9", emission_strength=2.0, alpha=.55)

    # A vertical explanatory slice: bright Sabaody surface, Red Line walls, dark trench.
    route_parts = [
        core.cube("Fish-Man descent surface ocean", (0, 0, 12.8), (8.8, 4.2, .32), surface, c.topology),
        core.cube("Fish-Man descent midwater volume", (0, 1.9, 7.0), (8.8, .4, 5.4), midwater, c.topology),
        core.cube("Fish-Man descent abyss floor", (0, 0, .1), (8.8, 4.2, .35), deep, c.topology),
        make_rock_slab("Undersea Red Line west wall", 6.1, 12.2, 3.0, 1.6, red, c.topology, phase=.3, vertices=20),
        make_rock_slab("Undersea Red Line east wall", 6.1, 12.2, 3.0, 1.6, strata, c.topology, phase=1.7, vertices=20),
    ]
    route_parts[-2].location.x = -6.5
    route_parts[-1].location.x = 6.5
    for depth_index, z in enumerate((10.5, 8.5, 6.5, 4.5, 2.5)):
        route_parts.append(core.curve(f"Descent depth contour {depth_index+1}", [(-3.4, 2.35, z), (0, 2.55, z-.15), (3.4, 2.35, z)], .025, current, c.topology))
    tag_many(route_parts, "red-line-undersea-route", 496)

    yard = [
        core.island("Sabaody coating yard root platform", (-4.4, -1.0, 13.35), 2.0, .38, strata, c.landmarks, (1.0, .72), 30),
        core.cube("Coating yard tool shed", (-4.7, -1.0, 14.0), (.62, .48, .55), ship, c.landmarks),
        core.torus("Coating yard resin vat", (-3.5, -1.15, 13.75), .55, .12, resin, c.landmarks),
        core.cylinder("Coating yard hose reel", (-4.0, -1.65, 13.78), .34, .16, sunny, c.landmarks, 20),
    ]
    tag_many(yard, "sabaody-coating-yard", 507)

    ship_parts = [
        core.sphere("Coated Sunny dive root bubble", (-2.5, 0, 12.25), (1.25, .9, .9), resin, c.states, 24, 14),
        core.cube("Coated Sunny hull", (-2.5, 0, 12.15), (.72, .38, .28), ship, c.states),
        core.cylinder("Coated Sunny mast", (-2.5, 0, 12.85), .05, 1.2, sunny, c.states, 12),
        core.cube("Coated Sunny sail", (-2.5, 0, 12.9), (.46, .045, .38), sail, c.states),
        core.sphere("Coated Sunny lion prow", (-1.72, 0, 12.22), (.22, .22, .22), sunny, c.states, 14, 8),
    ]
    for obj in ship_parts[1:]:
        parent_keep_world(obj, ship_parts[0])
    state_tag(ship_parts, "coated-sunny-dive", 602, 607.999)
    animate_location(ship_parts[0], "fishman_descent_route_state", [
        (1, (-2.5, 0, 12.25)), (25, (-1.3, 0, 10.1)), (49, (.3, 0, 7.9)),
        (73, (-.5, 0, 5.7)), (97, (1.25, 0, 3.35)), (121, (0, 0, 1.25)),
    ])

    pressure = [core.torus("Undersea pressure ring", (0, 0, 9.8), 2.2, .09, resin, c.states),
                core.sphere("Undersea light zone whale", (3.2, .4, 9.4), (1.45, .42, .48), creature, c.states, 18, 9)]
    state_tag(pressure, "undersea-pressure-zone", 603, 607.999)

    plume: list[bpy.types.Object] = []
    plume_root = core.curve("Downward plume animated root", [(2.8, 1.0, 9.0), (1.8, .7, 7.4), (.5, .3, 6.0), (-.4, 0, 4.5)], .24, current, c.states)
    plume.append(plume_root)
    for i in range(10):
        bubble = core.sphere(f"Downward plume bubble {i+1}", (2.7 - i * .32, .75, 8.8 - i * .42), (.11, .11, .14), resin, c.states, 10, 6)
        parent_keep_world(bubble, plume_root)
        plume.append(bubble)
    state_tag(plume, "downward-plume", 604, 607.999)
    animate_location(plume_root, "fishman_current_cycle", [(1, (0, 0, 0)), (61, (.35, 0, -.45)), (116, (0, 0, 0))])

    kraken: list[bpy.types.Object] = [core.sphere("Kraken route hazard head", (-3.4, .4, 7.0), (.72, .6, .62), kraken_mat, c.states, 18, 10)]
    for i in range(8):
        a = -1.2 + i * .34
        kraken.append(core.curve(f"Kraken route tentacle {i+1}", [(-3.4, .4, 6.7), (-3.4 + math.cos(a) * 1.2, .2, 5.8), (-3.4 + math.cos(a) * 2.2, 0, 5.0 + math.sin(a))], .11, kraken_mat, c.states))
    state_tag(kraken, "kraken-route-hazard", 604, 607.999)

    creatures: list[bpy.types.Object] = []
    for i in range(14):
        x = -4.8 + (i * 2.31) % 9.6
        z = 3.2 + (i * 1.13) % 2.3
        creatures.append(core.sphere(f"Underworld sea creature {i+1:02d}", (x, .65, z), (.45 + .12 * (i % 3), .2, .28), creature, c.states, 14, 7))
    state_tag(creatures, "underworld-sea-creatures", 605, 607.999)

    volcanic: list[bpy.types.Object] = []
    volcano_root = core.cone("Deep-sea volcanic root", (3.7, 0, 1.15), 1.25, .2, 2.0, red, c.states, 28)
    volcanic.append(volcano_root)
    for i in range(9):
        a = math.tau * i / 9
        vent = core.sphere(f"Deep-sea lava vent {i+1}", (3.7 + math.cos(a) * .55, math.sin(a) * .45, 2.05 + .15 * (i % 3)), (.18, .18, .25), lava, c.states, 12, 7)
        parent_keep_world(vent, volcano_root)
        volcanic.append(vent)
    state_tag(volcanic, "deep-sea-volcanic-region", 606, 607.999)
    animate_scale(volcano_root, "fishman_volcanic_cycle", [(1, (1, 1, 1)), (43, (1.08, 1.08, 1.22)), (86, (.96, .96, .9)), (121, (1, 1, 1))])

    trench = [core.cube("Red Line ten-thousand-meter trench", (0, 0, .48), (2.45, 1.8, .22), deep, c.states)]
    state_tag(trench, "red-line-trench-approach", 607, 607.999)
    distant = [core.sphere("Fish-Man Island distant gate", (0, 1.0, .85), (1.45, .45, .72), gate, c.states, 24, 12),
               core.torus("Fish-Man Island distant ring", (0, 1.0, .85), 1.25, .07, gate, c.states, rotation=(math.pi / 2, 0, 0))]
    state_tag(distant, "fish-man-island-distant-gate", 607, 607.999)

    result = core.finish(
        "fish-man-red-line-descent", contract, c, rx, ry,
        (20, -30, 16), (0, 0, 7.0), safe_full_chapter=507,
        layout_status="local_undersea_cross_section_not_survey_geometry",
    )
    bpy.context.scene.frame_end = 121
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "source/fish-man-red-line-descent.blend"))
    return result


BUILDERS = {
    "water-7-sea-train-network": build_water7,
    "mary-geoise-red-line": build_mary_geoise,
    "fish-man-red-line-descent": build_fishman_descent,
}


def main() -> int:
    args = cli_args()
    (ROOT / "source").mkdir(parents=True, exist_ok=True)
    (ROOT / "renders/runtime").mkdir(parents=True, exist_ok=True)
    selected = args.only or list(ASSETS)
    results = []
    for asset_id in selected:
        contract = json.loads((ROOT / f"contracts/{asset_id}.visual.json").read_text(encoding="utf-8"))
        print(f"BUILD {asset_id}")
        results.append(BUILDERS[asset_id](contract, args.resolution_x, args.resolution_y))
    print(json.dumps({"built": [row["id"] for row in results]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
