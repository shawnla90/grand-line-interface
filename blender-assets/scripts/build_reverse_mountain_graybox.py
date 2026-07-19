#!/usr/bin/env python3
"""Build the Reverse Mountain/Twin Cape W1 moving-world graybox.

The output is intentionally an authored local theatre, not geographic evidence.
MapLibre still owns the globe route, chapter, camera, and lifetime.  This scene
supplies tagged local geometry, named clips, control masks, and a transparent
fallback that can also be reused by an Unreal import adapter.

Run with Blender 4.5+:
  Blender --background --factory-startup --python \
    scripts/build_reverse_mountain_graybox.py
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "reverse-mountain-twin-cape-voyage"
SOURCE = ROOT / "source" / f"{ASSET_ID}.blend"
GLB = ROOT / "runtime" / f"{ASSET_ID}.glb"
SIDECAR = ROOT / "runtime" / f"{ASSET_ID}.model.json"
FALLBACK = ROOT / "renders" / "runtime" / f"{ASSET_ID}.png"
MASK_DIR = ROOT / "runtime" / ASSET_ID / "masks"
FPS = 30


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"Not a GLB: {path}")
    chunk_length, _ = struct.unpack("<II", data[12:20])
    return json.loads(data[20 : 20 + chunk_length])


def collection(name: str) -> bpy.types.Collection:
    value = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(value)
    return value


def move(obj: bpy.types.Object, target: bpy.types.Collection) -> bpy.types.Object:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def material(
    name: str,
    color: str,
    *,
    roughness: float = 0.65,
    metallic: float = 0.0,
    emission: str | None = None,
    emission_strength: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    rgb = tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    bsdf.inputs["Base Color"].default_value = (*rgb, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        ergb = tuple(int(emission[i : i + 2], 16) / 255 for i in (0, 2, 4))
        bsdf.inputs["Emission Color"].default_value = (*ergb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1:
        value.surface_render_method = "DITHERED"
    return value


def component_root(
    name: str,
    target: bpy.types.Collection,
    component_id: str,
    reveal: int | None,
    *,
    confidence: str = "verified",
    default_hidden: bool = False,
    active_through: float | None = None,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    target.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj["component_id"] = component_id
    obj["gate_confidence"] = confidence
    obj["default_hidden"] = default_hidden
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    if reveal is not None:
        obj["reveal_chapter"] = reveal
    if active_through is not None:
        obj["active_through_chapter"] = active_through
    return obj


def empty(name: str, target: bpy.types.Collection, parent: bpy.types.Object | None = None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    target.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.parent = parent
    return obj


def cube(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
    *,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def cone(
    name: str,
    location: tuple[float, float, float],
    radius1: float,
    radius2: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
    *,
    vertices: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
    *,
    segments: int = 32,
    rings: int = 16,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=48,
        minor_segments=10,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def ribbon(
    name: str,
    points: Iterable[tuple[float, float, float]],
    bevel: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    pts = list(points)
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(pts) - 1)
    for bp, point in zip(spline.bezier_points, pts):
        bp.co = point
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    obj.parent = parent
    obj["lod_tier"] = "LOD1_LOCAL_THEATRE"
    return obj


def reset_transform(obj: bpy.types.Object, loc: Vector, rot: Vector, scale: Vector) -> None:
    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scale


def hide_render_tree(root: bpy.types.Object, hidden: bool) -> None:
    root.hide_render = hidden
    for child in root.children_recursive:
        child.hide_render = hidden


def clip(
    obj: bpy.types.Object,
    name: str,
    keys: list[dict[str, Any]],
    *,
    loop: bool,
) -> None:
    """Create one named Action and associate it through a single-strip NLA track."""
    base_loc = obj.location.copy()
    base_rot = obj.rotation_euler.copy()
    base_scale = obj.scale.copy()
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
        if "scale" in key:
            obj.scale = key["scale"]
            obj.keyframe_insert(data_path="scale", frame=frame)
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
    obj[f"clip:{name}"] = "loop" if loop else "once"
    reset_transform(obj, base_loc, base_rot, base_scale)


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def create_masks() -> list[dict[str, Any]]:
    MASK_DIR.mkdir(parents=True, exist_ok=True)
    specs = [
        ("rm-current-flow-rgba", "current_flow", False),
        ("rm-foam-spray-rgba", "foam_spray", False),
        ("merry-hull-contact-rgba", "hull_contact", False),
        ("laboon-water-contact-rgba", "laboon_contact", False),
        ("whirlpool-control-rgba", "whirlpool", True),
    ]
    out: list[dict[str, Any]] = []
    size = 256
    for mask_id, mode, hidden in specs:
        image = bpy.data.images.new(mask_id, width=size, height=size, alpha=True, float_buffer=False)
        pixels: list[float] = []
        for y in range(size):
            v = y / (size - 1)
            for x in range(size):
                u = x / (size - 1)
                dx, dy = u - 0.5, v - 0.5
                radius = min(1.0, math.hypot(dx, dy) * 2)
                if mode == "current_flow":
                    r, g, b, a = u, 1 - v, 0.35 + 0.65 * (1 - abs(u - 0.5) * 2), 1.0
                elif mode == "foam_spray":
                    bank = min(1.0, abs(u - 0.5) * 2.4)
                    crest = max(0.0, 1 - abs(v - 0.72) * 8)
                    r, g, b, a = bank, crest, max(bank, crest), 1 - radius * 0.25
                elif mode == "hull_contact":
                    bow = max(0.0, 1 - math.hypot((u - 0.5) * 2.5, (v - 0.78) * 4))
                    stern = max(0.0, 1 - math.hypot((u - 0.5) * 2.5, (v - 0.22) * 4))
                    r, g, b, a = bow, stern, 1 - radius, max(bow, stern)
                elif mode == "laboon_contact":
                    edge = max(0.0, 1 - abs(radius - 0.72) * 7)
                    r, g, b, a = 1 - radius, edge, max(0.0, 1 - radius * 1.6), 1 - radius * 0.35
                else:
                    angle = (math.atan2(dy, dx) / (2 * math.pi)) % 1
                    ring = max(0.0, 1 - abs(radius - 0.62) * 8)
                    r, g, b, a = 1 - radius, ring, angle, 0.0
                pixels.extend((r, g, b, a))
        image.pixels.foreach_set(pixels)
        path = MASK_DIR / f"{mask_id}.png"
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
        out.append(
            {
                "id": mask_id,
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "pixel_size": [size, size],
                "default_hidden": hidden,
            }
        )
    return out


def build() -> list[dict[str, Any]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(FALLBACK)
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 180
    scene.world = bpy.data.worlds.new("Reverse Mountain review world")
    scene.world.color = (0.004, 0.008, 0.02)

    env = collection("00_ENVIRONMENT")
    landmarks = collection("10_LANDMARKS")
    routes = collection("20_ROUTES")
    vehicle = collection("30_VEHICLE")
    creature = collection("40_CREATURE")
    states = collection("50_EVENT_STATES")
    fx = collection("60_FX_CONTROLS")
    collection("70_RUNTIME_LOD")
    helpers = collection("80_EXPORT_HELPERS")

    water = material("RM_Water", "163b63", roughness=0.26, metallic=0.18)
    current = material("RM_Current", "3ba6c6", roughness=0.22, emission="38b8d8", emission_strength=0.38)
    foam = material("RM_Foam", "d9f5ed", roughness=0.34, emission="bcefff", emission_strength=0.4)
    red_rock = material("RM_Red_Line", "7b2d38", roughness=0.82)
    red_light = material("RM_Red_Line_Highlight", "a94b49", roughness=0.78)
    stone = material("RM_Stone", "715f63", roughness=0.88)
    grass = material("RM_Cape_Grass", "496b50", roughness=0.9)
    lighthouse = material("RM_Lighthouse", "e7d7bd", roughness=0.7)
    beacon = material("RM_Beacon", "f4c75d", emission="ffcf5b", emission_strength=2.2)
    hull = material("Merry_Hull", "7a3c2b", roughness=0.62)
    trim = material("Merry_Trim", "e2b36f", roughness=0.55)
    sail = material("Merry_Sail", "e8e0cc", roughness=0.75)
    dark = material("Merry_Dark", "1a2430", roughness=0.7)
    laboon_blue = material("Laboon_Blue", "284e76", roughness=0.48)
    laboon_belly = material("Laboon_Belly", "8bb4c0", roughness=0.55)
    scar = material("Laboon_Scar", "8f3d45", roughness=0.7)
    interior = material("Laboon_Interior", "5c334f", roughness=0.62, emission="4b233f", emission_strength=0.25)
    haze = material("RM_Haze", "9dddec", roughness=0.2, emission="77d6e8", emission_strength=0.35, alpha=0.42)

    massif = component_root("COMP_REVERSE_MOUNTAIN_MASSIF", env, "reverse-mountain-massif", 101)
    # A broad local-theatre water plate. The local arrangement is deliberately schematic.
    cylinder("Grand Line local water", (0, 0, -0.5), 18.0, 0.75, water, env, massif, vertices=96)
    for side in (-1, 1):
        for i, (y, z, radius, height) in enumerate(
            [(-9, 1.2, 5.4, 5.0), (-5, 3.0, 5.8, 8.0), (-1, 4.8, 6.4, 11.0), (3, 3.5, 6.0, 8.5)]
        ):
            x = side * (3.8 + (i % 2) * 0.6)
            peak = cone(f"Red Line peak {side} {i}", (x, y, z), radius, radius * 0.16, height, red_rock, env, massif, vertices=40)
            peak.rotation_euler[1] = side * 0.08
            cone(f"Red Line cap {side} {i}", (x * 1.01, y, z + height * 0.34), radius * 0.5, 0.1, height * 0.33, red_light, env, massif, vertices=32)

    ascent = component_root("COMP_EAST_BLUE_ASCENT_CURRENT", routes, "east-blue-ascent-current", 101)
    ascent_points = [(0, -15, 0.2), (0.3, -11, 1.0), (-0.25, -7, 3.1), (0.15, -3.2, 6.5), (0, -0.6, 8.0)]
    ribbon("East Blue uphill current", ascent_points, 1.25, current, routes, ascent)
    ribbon("Ascent foam port", [(x - 1.05, y, z + 0.08) for x, y, z in ascent_points], 0.12, foam, routes, ascent)
    ribbon("Ascent foam starboard", [(x + 1.05, y, z + 0.08) for x, y, z in ascent_points], 0.12, foam, routes, ascent)

    crest = component_root("COMP_REVERSE_MOUNTAIN_CREST", landmarks, "reverse-mountain-crest", 101)
    torus("Reverse Mountain crest halo", (0, 0, 8.1), 2.0, 0.25, foam, landmarks, crest).rotation_euler[0] = math.pi / 2
    for x in (-2.6, 2.6):
        cone("Crest needle", (x, 0, 8.1), 1.2, 0.15, 4.5, red_light, landmarks, crest, vertices=28)

    descent = component_root("COMP_GRAND_LINE_DESCENT_CURRENT", routes, "grand-line-descent-current", 102)
    descent_points = [(0, 0.6, 8.0), (0.25, 3.2, 6.4), (-0.2, 6.5, 3.5), (0.15, 9.5, 1.2), (0, 11.5, 0.25)]
    ribbon("Grand Line descent current", descent_points, 1.25, current, routes, descent)
    ribbon("Descent foam port", [(x - 1.05, y, z + 0.08) for x, y, z in descent_points], 0.12, foam, routes, descent)
    ribbon("Descent foam starboard", [(x + 1.05, y, z + 0.08) for x, y, z in descent_points], 0.12, foam, routes, descent)

    cape = component_root("COMP_TWIN_CAPE", env, "twin-cape", 102)
    for x, y, sx, sy in [(-6.0, 12.4, 4.6, 2.6), (5.8, 12.9, 4.3, 2.5)]:
        rock = sphere("Twin Cape rock", (x, y, 0.35), (sx, sy, 0.9), stone, env, cape, segments=32, rings=12)
        rock.rotation_euler[2] = x * 0.025
        sphere("Twin Cape grass", (x, y - 0.1, 0.85), (sx * 0.86, sy * 0.86, 0.45), grass, env, cape, segments=28, rings=10)

    light_root = component_root("COMP_TWIN_CAPE_LIGHTHOUSE", landmarks, "twin-cape-lighthouse", 103)
    cylinder("Twin Cape lighthouse tower", (5.8, 12.8, 2.45), 0.58, 4.2, lighthouse, landmarks, light_root, vertices=28)
    cone("Twin Cape lighthouse roof", (5.8, 12.8, 4.75), 0.92, 0.08, 0.95, dark, landmarks, light_root, vertices=28)
    cylinder("Twin Cape beacon", (5.8, 12.8, 4.23), 0.48, 0.52, beacon, landmarks, light_root, vertices=24)

    merry = component_root("RIG_GOING_MERRY", vehicle, "going-merry", 100)
    merry.location = (0, -12.4, 0.85)
    hull_body = sphere("Going Merry hull", (0, 0, 0), (1.15, 2.45, 0.68), hull, vehicle, merry, segments=32, rings=12)
    hull_body.rotation_euler[2] = 0
    cube("Going Merry deck", (0, 0.1, 0.54), (0.9, 1.72, 0.12), trim, vehicle, merry)
    cylinder("Going Merry mast", (0, 0, 2.3), 0.1, 4.2, dark, vehicle, merry, vertices=16)
    main_sail = cube("Going Merry main sail", (0, 0.15, 2.55), (1.28, 0.05, 1.25), sail, vehicle, merry)
    main_sail.rotation_euler[1] = -0.05
    cylinder("Going Merry sheep head", (0, 2.48, 0.45), 0.45, 0.52, sail, vehicle, merry, vertices=24).rotation_euler[0] = math.pi / 2
    for x in (-0.36, 0.36):
        horn = torus("Going Merry horn", (x, 2.55, 0.55), 0.27, 0.08, trim, vehicle, merry)
        horn.rotation_euler = (math.pi / 2, 0, 0)
    for x in (-0.16, 0.16):
        sphere("Going Merry eye", (x, 2.72, 0.58), (0.07, 0.05, 0.08), dark, vehicle, merry, segments=12, rings=8)
    wake_control = empty("CTRL_MERRY_WAKE", fx, merry)
    wake_control["fx_mask"] = "merry-hull-contact-rgba"

    laboon = component_root("RIG_LABOON", creature, "laboon-unidentified", 102)
    laboon.location = (0, 14.2, 1.25)
    body = sphere("Laboon body", (0, 0, 0), (4.8, 6.6, 3.6), laboon_blue, creature, laboon, segments=40, rings=20)
    body.rotation_euler[2] = 0
    sphere("Laboon belly", (0, -0.6, -1.0), (4.25, 5.5, 2.55), laboon_belly, creature, laboon, segments=36, rings=16)
    jaw = cube("Laboon lower jaw", (0, -4.95, -0.55), (3.65, 1.1, 0.55), laboon_belly, creature, laboon)
    jaw.rotation_euler[0] = -0.04
    for x in (-3.7, 3.7):
        fin = sphere("Laboon side fin", (x, 0.2, -0.4), (2.25, 0.55, 0.34), laboon_blue, creature, laboon, segments=24, rings=10)
        fin.rotation_euler[1] = x * 0.045
    for x in (-1.8, 1.8):
        tail = sphere("Laboon tail", (x, 6.35, 0.15), (2.1, 1.0, 0.35), laboon_blue, creature, laboon, segments=24, rings=10)
        tail.rotation_euler[2] = x * 0.12
    for x in (-1.15, 0, 1.15):
        ribbon("Laboon forehead scar", [(x - 0.7, -5.7, 1.65), (x, -6.0, 2.2), (x + 0.65, -5.72, 2.6)], 0.09, scar, creature, laboon)
    identity = empty("META_LABOON_IDENTITY_REVEAL", creature, laboon)
    identity["component_id"] = "laboon"
    identity["gate_confidence"] = "verified"
    identity["default_hidden"] = False
    identity["reveal_chapter"] = 103
    breath_control = empty("CTRL_LABOON_BREATH", fx, laboon)
    breath_control.location = (0, -5.4, 3.0)
    breath_control["fx_mask"] = "laboon-water-contact-rgba"

    interior_root = component_root(
        "COMP_LABOON_INTERIOR_THEATRE",
        states,
        "laboon-interior-theatre",
        103,
        confidence="verified_state_window",
        default_hidden=True,
        active_through=103.999,
    )
    interior_root.location = (-11.2, 8.2, 1.2)
    sphere("Laboon interior shell", (0, 0, 2.3), (5.0, 3.5, 3.6), interior, states, interior_root, segments=32, rings=16)
    cylinder("Interior water stage", (0, 0, 0), 4.2, 0.45, water, states, interior_root, vertices=48)
    cube("Interior Merry proxy stage", (0, 0.5, 0.55), (0.65, 1.25, 0.35), hull, states, interior_root)

    crocus = component_root("ANCHOR_CROCUS_2_5D", states, "crocus", 103)
    crocus.location = (-8.6, 7.2, 1.3)
    crocus["story_actor_slot"] = "crocus-reverse-mountain"
    straw_hat_anchor = empty("ANCHOR_STRAW_HATS_2_5D", states)
    straw_hat_anchor.location = (-4.8, 12.0, 1.2)
    straw_hat_anchor["story_actor_slot"] = "straw-hats-reverse-mountain"
    straw_hat_anchor["reveal_chapter"] = 104

    whirlpool = component_root(
        "CTRL_LOCAL_WHIRLPOOL",
        fx,
        "local-whirlpool-emitter",
        None,
        confidence="chapter_to_verify",
        default_hidden=True,
    )
    whirlpool.location = (10.5, -4.0, 0.05)
    torus("Whirlpool foam ring", (0, 0, 0), 2.4, 0.22, foam, fx, whirlpool)
    for radius in (0.7, 1.2, 1.7):
        torus("Whirlpool control ring", (0, 0, -0.04 * radius), radius, 0.08, current, fx, whirlpool)
    whirlpool["fx_mask"] = "whirlpool-control-rgba"

    current_control = empty("CTRL_ASCENT_CURRENT", fx, ascent)
    current_control["fx_mask"] = "rm-current-flow-rgba"
    crest_control = empty("CTRL_CREST_SURGE", fx, crest)
    descent_control = empty("CTRL_DESCENT_CURRENT", fx, descent)
    swell_control = empty("CTRL_TWIN_CAPE_SWELL", fx, cape)
    contact_control = empty("CTRL_LABOON_CONTACT", fx, laboon)
    contact_control["fx_mask"] = "laboon-water-contact-rgba"

    # Exact contract clips. Transform keys are local-theatre motion only; the
    # world route stays in MapLibre and is never baked into these actions.
    clip(merry, "merry_idle_bob_loop", [
        {"frame": 1, "location": (0, 11.0, 0.8), "rotation": (0, 0, -0.035)},
        {"frame": 31, "location": (0, 11.0, 1.02), "rotation": (0, 0, 0.035)},
        {"frame": 61, "location": (0, 11.0, 0.8), "rotation": (0, 0, -0.035)},
    ], loop=True)
    clip(merry, "merry_ascent_climb", [
        {"frame": 1, "location": (0, -13.8, 0.65), "rotation": (-0.08, 0, 0)},
        {"frame": 45, "location": (0.2, -8.0, 2.7), "rotation": (-0.22, 0, -0.03)},
        {"frame": 90, "location": (-0.1, -3.0, 6.5), "rotation": (-0.32, 0, 0.025)},
    ], loop=False)
    clip(merry, "merry_summit_crest", [
        {"frame": 1, "location": (-0.1, -3.0, 6.5), "rotation": (-0.32, 0, 0.02)},
        {"frame": 38, "location": (0, 0, 8.15), "rotation": (0, 0, 0)},
        {"frame": 70, "location": (0.12, 2.8, 6.6), "rotation": (0.28, 0, -0.02)},
    ], loop=False)
    clip(merry, "merry_descent_run", [
        {"frame": 1, "location": (0.12, 2.8, 6.6), "rotation": (0.28, 0, -0.02)},
        {"frame": 45, "location": (-0.1, 7.0, 3.4), "rotation": (0.24, 0, 0.03)},
        {"frame": 80, "location": (0, 10.5, 1.0), "rotation": (0.08, 0, 0)},
    ], loop=False)
    clip(merry, "merry_swallowed_transition", [
        {"frame": 1, "location": (0, 10.5, 1.0), "rotation": (0, 0, 0), "scale": (1, 1, 1)},
        {"frame": 40, "location": (0, 12.4, 1.4), "rotation": (0.04, 0, 0), "scale": (0.78, 0.78, 0.78)},
        {"frame": 70, "location": (0, 14.0, 1.7), "rotation": (0.08, 0, 0), "scale": (0.08, 0.08, 0.08)},
    ], loop=False)
    clip(merry, "merry_twin_cape_departure", [
        {"frame": 1, "location": (-2.8, 10.5, 0.85), "rotation": (0, 0, -0.08), "scale": (1, 1, 1)},
        {"frame": 55, "location": (-0.4, 15.8, 0.9), "rotation": (0, 0, 0.02), "scale": (1, 1, 1)},
        {"frame": 100, "location": (2.8, 20.0, 0.9), "rotation": (0, 0, 0.12), "scale": (1, 1, 1)},
    ], loop=False)

    clip(laboon, "laboon_surface_idle_loop", [
        {"frame": 1, "location": (0, 14.2, 1.0), "rotation": (0, 0, -0.018)},
        {"frame": 45, "location": (0, 14.2, 1.35), "rotation": (0, 0, 0.018)},
        {"frame": 90, "location": (0, 14.2, 1.0), "rotation": (0, 0, -0.018)},
    ], loop=True)
    clip(laboon, "laboon_first_contact_breach", [
        {"frame": 1, "location": (0, 17.0, -3.2), "rotation": (0.1, 0, 0)},
        {"frame": 38, "location": (0, 14.8, 2.4), "rotation": (-0.08, 0, 0)},
        {"frame": 78, "location": (0, 14.2, 1.1), "rotation": (0, 0, 0)},
    ], loop=False)
    clip(jaw, "laboon_mouth_open_swallow", [
        {"frame": 1, "rotation": (-0.04, 0, 0)},
        {"frame": 30, "rotation": (-0.48, 0, 0)},
        {"frame": 70, "rotation": (-0.62, 0, 0)},
        {"frame": 100, "rotation": (-0.08, 0, 0)},
    ], loop=False)
    clip(breath_control, "laboon_breath_mist", [
        {"frame": 1, "scale": (0.1, 0.1, 0.1)},
        {"frame": 35, "scale": (2.2, 2.2, 2.2)},
        {"frame": 70, "scale": (0.1, 0.1, 0.1)},
    ], loop=False)
    clip(laboon, "laboon_promise_response", [
        {"frame": 1, "location": (0, 14.2, 1.1), "rotation": (0, 0, 0)},
        {"frame": 42, "location": (0, 14.0, 2.0), "rotation": (-0.06, 0, 0.05)},
        {"frame": 86, "location": (0, 14.2, 1.1), "rotation": (0, 0, -0.03)},
    ], loop=False)

    clip(crocus, "crocus_idle_watch", [
        {"frame": 1, "rotation": (0, 0, -0.02)}, {"frame": 60, "rotation": (0, 0, 0.02)}, {"frame": 120, "rotation": (0, 0, -0.02)}
    ], loop=True)
    clip(crocus, "crocus_explain_laboon", [
        {"frame": 1, "rotation": (0, 0, 0)}, {"frame": 40, "rotation": (0, 0, -0.18)}, {"frame": 80, "rotation": (0, 0, 0.08)}
    ], loop=False)
    clip(crocus, "crocus_present_log_pose", [
        {"frame": 1, "location": (-8.6, 7.2, 1.3)}, {"frame": 45, "location": (-8.1, 7.2, 1.55)}, {"frame": 85, "location": (-8.6, 7.2, 1.3)}
    ], loop=False)

    fx_clips = [
        (current_control, "current_ascent_flow_loop", True),
        (crest_control, "current_crest_surge", False),
        (descent_control, "current_descent_flow_loop", True),
        (swell_control, "twin_cape_swell_loop", True),
        (wake_control, "merry_wake_loop", True),
        (contact_control, "laboon_contact_displacement", False),
        (whirlpool, "whirlpool_loop_default_hidden", True),
    ]
    for control, name, loop in fx_clips:
        clip(control, name, [
            {"frame": 1, "scale": (0.94, 0.94, 0.94), "rotation": (0, 0, 0)},
            {"frame": 31, "scale": (1.08, 1.08, 1.08), "rotation": (0, 0, 0.12)},
            {"frame": 61, "scale": (0.94, 0.94, 0.94), "rotation": (0, 0, 0.24)},
        ], loop=loop)

    # Review camera and light are source-only helpers and never selected for GLB.
    bpy.ops.object.camera_add(location=(30, -31, 23))
    camera = bpy.context.object
    camera.name = "CAM_REVERSE_MOUNTAIN_REVIEW"
    move(camera, helpers)
    look_at(camera, (0, 1.5, 3.0))
    camera.data.lens = 47
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(-12, -10, 25))
    key_light = bpy.context.object
    key_light.name = "KEY_REVIEW_ONLY"
    key_light.data.energy = 1850
    key_light.data.shape = "DISK"
    key_light.data.size = 14
    move(key_light, helpers)
    look_at(key_light, (0, 2, 2))
    bpy.ops.object.light_add(type="AREA", location=(15, 8, 12))
    fill_light = bpy.context.object
    fill_light.name = "FILL_REVIEW_ONLY"
    fill_light.data.energy = 1100
    fill_light.data.size = 12
    move(fill_light, helpers)
    look_at(fill_light, (0, 7, 1))

    # Freeze the editable file in a readable chapter-102 exterior tableau.
    # The fallback obeys that same gate: no lighthouse, interior, Crocus, or
    # unsupported whirlpool appears in its pixels.
    reset_transform(merry, Vector((4.8, 5.8, 4.1)), Vector((-0.12, 0, -0.16)), Vector((1.35, 1.35, 1.35)))
    reset_transform(laboon, Vector((1.8, 14.8, 3.0)), Vector((0, 0, -0.04)), Vector((1, 1, 1)))
    for gated_root in (light_root, interior_root, whirlpool):
        hide_render_tree(gated_root, True)
    scene["asset_id"] = ASSET_ID
    scene["layout_status"] = "ordered_route_graph_not_atlas_geometry"
    scene["runtime_owner"] = "MapLibre journey director"
    scene["story_actor_medium"] = "signed 2.5D atlas"
    scene["lod_built"] = "LOD1_LOCAL_THEATRE"

    for path in (SOURCE, GLB, SIDECAR, FALLBACK):
        path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    scene.render.filepath = str(FALLBACK)
    bpy.ops.render.render(write_still=True)

    # Runtime receives every tagged node. Restore render flags and neutral base
    # transforms before export; the exact actions own motion after load.
    for gated_root in (light_root, interior_root, whirlpool):
        hide_render_tree(gated_root, False)
    reset_transform(merry, Vector((0, -12.4, 0.85)), Vector((0, 0, 0)), Vector((1, 1, 1)))
    reset_transform(laboon, Vector((0, 14.2, 1.25)), Vector((0, 0, 0)), Vector((1, 1, 1)))

    exportable = [obj for obj in scene.objects if obj.type in {"MESH", "CURVE", "EMPTY"}]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in exportable:
        obj.hide_viewport = False
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = exportable[0]
    bpy.ops.export_scene.gltf(
        filepath=str(GLB),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=False,
        export_optimize_animation_size=True,
        export_optimize_animation_keep_anim_object=True,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_yup=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_use_gltfpack=False,
        check_existing=False,
    )
    return create_masks()


def finish(masks: list[dict[str, Any]]) -> None:
    payload = glb_json(GLB)
    animations = []
    for animation in payload.get("animations", []):
        duration = 0.0
        for sampler in animation.get("samplers", []):
            accessor = payload["accessors"][sampler["input"]]
            values = accessor.get("max") or [0]
            duration = max(duration, float(values[0]))
        animations.append({"name": animation.get("name"), "duration_seconds": round(duration, 4)})

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    vertices = sum(len(obj.data.vertices) for obj in meshes)
    triangles = sum(max(1, len(poly.vertices) - 2) for obj in meshes for poly in obj.data.polygons)
    materials = {slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)

    report = {
        "schema_version": 2,
        "id": ASSET_ID,
        "source_blend": str(SOURCE),
        "runtime_glb": str(GLB),
        "contract": "contracts/reverse-mountain-twin-cape-voyage.visual.json",
        "model_units": "authored local-theatre units; visual fit, not canon metres",
        "coordinate_system": "glTF 2.0 Y-up; Blender source Z-up",
        "export": {
            "exporter": "Blender built-in glTF 2.0 exporter",
            "animations": True,
            "animation_mode": "ACTIONS",
            "named_clips": animations,
            "extras": True,
            "textures_embedded": False,
        },
        "lod": {
            "built": "LOD1_LOCAL_THEATRE",
            "triangle_budget": {
                "environment": 70000,
                "going_merry": 35000,
                "laboon": 45000,
            },
            "remaining": ["LOD0_CLOSE_INSET", "LOD2_GLOBE", "LOD3_FALLBACK_COMPONENTS"],
        },
        "fx_masks": masks,
        "stats": {
            "objects": len(meshes),
            "vertices_input": vertices,
            "triangles_input": triangles,
            "materials": len(materials),
            "bounds_blender": {
                "min": [round(v, 6) for v in minimum],
                "max": [round(v, 6) for v in maximum],
            },
            "bytes": GLB.stat().st_size,
        },
        "fallback": {
            "path": str(FALLBACK.relative_to(ROOT)),
            "bytes": FALLBACK.stat().st_size,
            "sha256": sha256(FALLBACK),
            "pixel_size": [1200, 900],
            "alpha": True,
            "tableau": "chapter-102 exterior; label remains Unidentified giant whale in app state",
        },
        "build": {
            "blender": bpy.app.version_string,
            "glb_sha256": sha256(GLB),
            "glb_header": {
                "magic": "glTF",
                "version": 2,
                "declared_length": GLB.stat().st_size,
            },
        },
    }
    SIDECAR.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"SOURCE={SOURCE}")
    print(f"GLB={GLB} ({GLB.stat().st_size:,} bytes)")
    print(f"FALLBACK={FALLBACK} ({FALLBACK.stat().st_size:,} bytes)")
    print(f"ANIMATIONS={len(animations)}")
    print("CLIPS=" + ",".join(a["name"] or "" for a in animations))
    print(f"MASKS={len(masks)}")
    print(f"TRIANGLES={triangles:,}")


if __name__ == "__main__":
    finish(build())
