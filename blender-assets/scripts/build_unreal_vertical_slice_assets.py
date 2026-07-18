#!/usr/bin/env python3
"""Build original Baratie-slice environment and ship-proxy runtime GLBs.

These are deliberately stylized prototype assets. They encode encounter,
camera, approach, and buoyancy anchors without copying franchise logos, exact
ship silhouettes, or production meshes.

Run with Blender 4.5+:
  Blender --background --python \
    blender-assets/scripts/build_unreal_vertical_slice_assets.py
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
RUNTIME = ROOT / "runtime/unreal"
RENDERS = ROOT / "renders/unreal"
MANIFEST = ROOT / "manifests/unreal-vertical-slice-assets.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_collection(name: str) -> bpy.types.Collection:
    value = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(value)
    return value


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)


def material(
    name: str,
    color: str,
    roughness: float = 0.65,
    metallic: float = 0.0,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    rgb = tuple(int(color[index:index + 2], 16) / 255 for index in (0, 2, 4))
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return value


def tag_runtime(obj: bpy.types.Object, component_id: str, role: str) -> bpy.types.Object:
    obj["component_id"] = component_id
    obj["runtime_role"] = role
    obj["source_maturity"] = "unreal_vertical_slice_blockout_v1"
    return obj


def box(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    role: str = "environment_mesh",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    return tag_runtime(obj, name, role)


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    vertices: int = 48,
    scale_xy: tuple[float, float] = (1.0, 1.0),
    role: str = "environment_mesh",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale.x, obj.scale.y = scale_xy
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    return tag_runtime(obj, name, role)


def cone(
    name: str,
    location: tuple[float, float, float],
    radius1: float,
    radius2: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    vertices: int = 48,
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
    move_to_collection(obj, target)
    return tag_runtime(obj, name, "environment_mesh")


def beam(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    width: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    a = Vector(start)
    b = Vector(end)
    obj = box(name, tuple((a + b) * 0.5), (width, width, (b - a).length * 0.5), mat, target)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def anchor(
    name: str,
    location: tuple[float, float, float],
    target: bpy.types.Collection,
    role: str,
    forward: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.8
    target.objects.link(obj)
    tag_runtime(obj, name, "anchor")
    obj["anchor_role"] = role
    if forward:
        obj["forward_x"], obj["forward_y"], obj["forward_z"] = forward
    return obj


def add_preview_scene(
    target: bpy.types.Collection,
    camera_location: tuple[float, float, float],
    camera_target: tuple[float, float, float],
    water_size: float,
) -> bpy.types.Camera:
    preview_water = material("preview_water", "176B82", 0.18, 0.08)
    water = cylinder(
        "PREVIEW_WATER",
        (0, 0, -0.35),
        water_size,
        0.3,
        preview_water,
        target,
        vertices=64,
        role="preview_only",
    )
    water["preview_only"] = True

    world = bpy.context.scene.world or bpy.data.worlds.new("GrandLinePreviewWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.018, 0.05, 0.08, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45

    bpy.ops.object.light_add(type="AREA", location=(8, -12, 22))
    key = bpy.context.object
    key.name = "PREVIEW_KEY"
    key.data.energy = 1900
    key.data.shape = "DISK"
    key.data.size = 10
    key.data.color = (1.0, 0.76, 0.52)
    move_to_collection(key, target)
    key["preview_only"] = True

    bpy.ops.object.light_add(type="AREA", location=(-14, 4, 10))
    fill = bpy.context.object
    fill.name = "PREVIEW_FILL"
    fill.data.energy = 1200
    fill.data.size = 12
    fill.data.color = (0.22, 0.58, 1.0)
    move_to_collection(fill, target)
    fill["preview_only"] = True

    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.name = "PREVIEW_CAMERA"
    direction = Vector(camera_target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 52
    move_to_collection(camera, target)
    camera["preview_only"] = True
    bpy.context.scene.camera = camera
    return camera.data


def scene_settings(output: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output)
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"


def runtime_objects(runtime: bpy.types.Collection) -> list[bpy.types.Object]:
    return [
        obj
        for obj in runtime.all_objects
        if obj.type in {"MESH", "EMPTY"} and not bool(obj.get("preview_only", False))
    ]


def mesh_stats(objects: list[bpy.types.Object]) -> dict[str, Any]:
    meshes = [obj for obj in objects if obj.type == "MESH"]
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    vertices = 0
    triangles = 0
    materials = set()
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)
        vertices += len(obj.data.vertices)
        triangles += sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
        materials.update(
            slot.material.name for slot in obj.material_slots if slot.material is not None
        )
    return {
        "objects": len(meshes),
        "anchors": len([obj for obj in objects if obj.type == "EMPTY"]),
        "vertices_input": vertices,
        "triangles_input": triangles,
        "materials": len(materials),
        "bounds_blender_m": {
            "min": [round(value, 5) for value in minimum],
            "max": [round(value, 5) for value in maximum],
        },
    }


def export_runtime(asset_id: str, runtime: bpy.types.Collection) -> tuple[Path, dict[str, Any]]:
    output = RUNTIME / f"{asset_id}.glb"
    output.parent.mkdir(parents=True, exist_ok=True)
    candidates = runtime_objects(runtime)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in candidates:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(obj for obj in candidates if obj.type == "MESH")
    stats = mesh_stats(candidates)
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_yup=True,
        export_use_gltfpack=False,
        export_image_format="AUTO",
        export_materials="EXPORT",
        check_existing=False,
    )
    with output.open("rb") as handle:
        magic, version, declared_length = struct.unpack("<4sII", handle.read(12))
    if magic != b"glTF" or version != 2 or declared_length != output.stat().st_size:
        raise RuntimeError(f"Invalid exported GLB: {output}")
    stats["bytes"] = output.stat().st_size
    return output, stats


def finish_asset(
    asset_id: str,
    runtime: bpy.types.Collection,
    preview: bpy.types.Collection,
    anchor_names: list[str],
    scene_ids: list[str],
    place_id: str,
    kind: str,
) -> dict[str, Any]:
    SOURCE.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    blend = SOURCE / f"{asset_id}.blend"
    render = RENDERS / f"{asset_id}.png"
    scene_settings(render)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)
    glb, stats = export_runtime(asset_id, runtime)
    return {
        "id": asset_id,
        "kind": kind,
        "label": asset_id.replace("-", " ").title(),
        "maturity": "unreal_vertical_slice_blockout_v1",
        "place_id": place_id,
        "scene_ids": scene_ids,
        "source_blend": blend.relative_to(ROOT).as_posix(),
        "runtime_glb": glb.relative_to(ROOT).as_posix(),
        "preview": render.relative_to(ROOT).as_posix(),
        "anchors": anchor_names,
        "units": "meters",
        "coordinate_system": "glTF 2.0 Y-up converted from Blender Z-up",
        "rights": {
            "original_prototype_geometry": True,
            "franchise_logos_included": False,
            "exact_production_mesh_copy": False,
            "distribution_status": "internal_prototype_rights_review_required",
        },
        "stats": stats,
        "build": {
            "blender": bpy.app.version_string,
            "glb_sha256": sha256_file(glb),
            "source_sha256": sha256_file(blend),
            "preview_sha256": sha256_file(render),
        },
    }


def build_baratie_deck() -> dict[str, Any]:
    reset_scene()
    runtime = make_collection("RUNTIME_BARATIE_DECK")
    preview = make_collection("PREVIEW_ONLY")
    wood = material("deck_warm_wood", "8A4F2A", 0.72)
    dark_wood = material("deck_dark_wood", "3F241D", 0.78)
    red = material("restaurant_red", "9E2A2B", 0.58)
    cream = material("restaurant_cream", "E6C98D", 0.7)
    gold = material("restaurant_gold", "D6A84A", 0.36, 0.35)
    roof = material("restaurant_roof", "612126", 0.52)
    encounter = material("encounter_inlay", "D9B66F", 0.48, 0.08)

    cylinder("main_deck", (0, 0, 0.55), 8.2, 1.1, wood, runtime, 64, (1.42, 1.0))
    cylinder("lower_hull", (0, 0.8, -0.45), 7.6, 1.4, dark_wood, runtime, 64, (1.38, 0.94))
    cylinder("encounter_inlay", (0, -3.0, 1.13), 3.3, 0.06, encounter, runtime, 64, (1.2, 0.75))
    box("approach_dock", (0, -9.0, 0.85), (2.5, 3.1, 0.28), wood, runtime)
    for side in (-1, 1):
        box(f"dock_fender_{side}", (side * 2.75, -9.0, 0.55), (0.22, 3.2, 0.55), dark_wood, runtime)

    cylinder("restaurant_body", (0, 1.6, 3.0), 4.0, 4.2, red, runtime, 48, (1.15, 0.92))
    cylinder("restaurant_band", (0, 1.6, 3.6), 4.12, 0.45, gold, runtime, 48, (1.15, 0.92))
    cylinder("upper_gallery", (0, 1.6, 5.5), 3.0, 1.6, cream, runtime, 48, (1.1, 0.88))
    cone("restaurant_roof", (0, 1.6, 7.2), 4.1, 0.7, 2.2, roof, runtime, 48)
    cylinder("roof_crown", (0, 1.6, 8.55), 0.7, 0.75, gold, runtime, 32)
    for index in range(8):
        angle = math.tau * index / 8
        x = math.cos(angle) * 3.4
        y = 1.6 + math.sin(angle) * 2.6
        box(f"window_{index:02d}", (x, y, 3.2), (0.38, 0.12, 0.65), cream, runtime)

    for index in range(16):
        angle = math.tau * index / 16
        x = math.cos(angle) * 10.9
        y = math.sin(angle) * 7.35
        if y < -6.0 and abs(x) < 3.8:
            continue
        cylinder(f"rail_post_{index:02d}", (x, y, 1.8), 0.12, 1.5, dark_wood, runtime, 12)
    for segment, (start, end) in enumerate(
        [
            ((-10.6, -3.0, 2.25), (-8.2, -6.1, 2.25)),
            ((8.2, -6.1, 2.25), (10.6, -3.0, 2.25)),
            ((-10.6, -3.0, 2.25), (-10.6, 3.5, 2.25)),
            ((10.6, -3.0, 2.25), (10.6, 3.5, 2.25)),
            ((-10.6, 3.5, 2.25), (-6.8, 6.3, 2.25)),
            ((6.8, 6.3, 2.25), (10.6, 3.5, 2.25)),
        ]
    ):
        beam(f"rail_beam_{segment:02d}", start, end, 0.11, dark_wood, runtime)

    anchors = [
        ("anchor_ship_approach", (0, -22, 0), "ship_approach", (0, 1, 0)),
        ("anchor_dock_arrival", (0, -11.5, 1.2), "dock_arrival", (0, 1, 0)),
        ("anchor_encounter_center", (0, -3.0, 1.25), "encounter_center", None),
        ("anchor_zoro_start", (-4.2, -3.0, 1.25), "actor_spawn", (1, 0, 0)),
        ("anchor_mihawk_start", (4.0, -3.0, 1.25), "actor_spawn", (-1, 0, 0)),
        ("anchor_encounter_camera", (0, -12.5, 5.8), "camera", (0, 1, 0)),
        ("anchor_return_to_ocean", (0, -17.0, 0.5), "transition", (0, -1, 0)),
    ]
    for name, location, role, forward in anchors:
        anchor(name, location, runtime, role, forward)
    add_preview_scene(preview, (25, -30, 22), (0, 0, 2.5), 34)
    return finish_asset(
        "baratie-encounter-deck",
        runtime,
        preview,
        [item[0] for item in anchors],
        ["baratie-zoro-vs-mihawk", "baratie-luffy-vs-krieg", "sanji-leaves-baratie"],
        "baratie",
        "environment",
    )


def lofted_hull(
    name: str,
    target: bpy.types.Collection,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    sections = [
        (-6.0, 2.1, -1.0),
        (-3.2, 3.0, -1.55),
        (1.8, 2.75, -1.4),
        (5.1, 1.65, -0.95),
        (6.4, 0.2, 0.0),
    ]
    vertices: list[tuple[float, float, float]] = []
    for y, width, bottom in sections:
        vertices.extend(
            [
                (-width, y, 0.7),
                (width, y, 0.7),
                (-width * 0.34, y, bottom),
                (width * 0.34, y, bottom),
            ]
        )
    faces: list[tuple[int, ...]] = []
    for index in range(len(sections) - 1):
        a = index * 4
        b = (index + 1) * 4
        faces.extend(
            [
                (a, b, b + 2, a + 2),
                (a + 1, a + 3, b + 3, b + 1),
                (a, a + 1, b + 1, b),
                (a + 2, b + 2, b + 3, a + 3),
            ]
        )
    faces.extend([(0, 2, 3, 1), (16, 17, 19, 18)])
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(mat)
    return tag_runtime(obj, name, "vehicle_mesh")


def build_ship_proxy() -> dict[str, Any]:
    reset_scene()
    runtime = make_collection("RUNTIME_SHIP_PROXY")
    preview = make_collection("PREVIEW_ONLY")
    hull_red = material("proxy_hull_red", "7D2E2E", 0.66)
    hull_dark = material("proxy_hull_dark", "2F2727", 0.78)
    deck = material("proxy_deck", "A66B38", 0.72)
    sail = material("proxy_sail", "E8D9B5", 0.88)
    trim = material("proxy_trim", "D5A548", 0.4, 0.28)
    glass = material("proxy_glass", "4E91A6", 0.22, 0.18)

    lofted_hull("original_sloop_hull", runtime, hull_red)
    box("ship_deck", (0, -0.4, 0.88), (2.45, 4.6, 0.22), deck, runtime, "vehicle_mesh")
    box("aft_cabin", (0, -3.6, 2.0), (1.65, 1.25, 1.0), hull_dark, runtime, "vehicle_mesh")
    box("aft_window", (0, -4.88, 2.15), (0.8, 0.08, 0.38), glass, runtime, "vehicle_mesh")
    cylinder("main_mast", (0, 0.35, 5.0), 0.18, 8.2, hull_dark, runtime, 20, role="vehicle_mesh")
    box("main_sail", (0, 0.55, 5.5), (2.8, 0.1, 2.55), sail, runtime, "vehicle_mesh")
    box("sail_trim_top", (0, 0.55, 8.05), (3.0, 0.13, 0.11), trim, runtime, "vehicle_mesh")
    box("sail_trim_bottom", (0, 0.55, 2.95), (3.0, 0.13, 0.11), trim, runtime, "vehicle_mesh")
    cylinder("bow_spar", (0, 6.15, 1.75), 0.12, 3.1, hull_dark, runtime, 16, role="vehicle_mesh").rotation_euler[0] = math.radians(90)
    cylinder("stern_lantern", (0, -5.45, 3.45), 0.28, 0.65, trim, runtime, 16, role="vehicle_mesh")
    for side in (-1, 1):
        for y in (-3.8, -1.6, 0.8, 3.0):
            cylinder(
                f"rail_post_{side}_{y}",
                (side * 2.55, y, 1.55),
                0.08,
                1.1,
                hull_dark,
                runtime,
                10,
                role="vehicle_mesh",
            )
        beam(
            f"rail_{side}",
            (side * 2.55, -4.0, 2.05),
            (side * 2.55, 3.6, 2.05),
            0.08,
            hull_dark,
            runtime,
        )["runtime_role"] = "vehicle_mesh"

    anchors = [
        ("anchor_ship_root", (0, 0, 0), "vehicle_root", (0, 1, 0)),
        ("anchor_camera_chase", (0, -11.5, 6.3), "camera", (0, 1, -0.2)),
        ("anchor_camera_orbit", (0, 0, 2.0), "camera_pivot", None),
        ("anchor_bow", (0, 6.6, 1.2), "bow", (0, 1, 0)),
        ("anchor_wake", (0, -6.3, -0.1), "wake", (0, -1, 0)),
        ("anchor_buoyancy_fore_port", (-1.65, 3.2, -0.35), "buoyancy", None),
        ("anchor_buoyancy_fore_starboard", (1.65, 3.2, -0.35), "buoyancy", None),
        ("anchor_buoyancy_aft_port", (-1.8, -3.5, -0.35), "buoyancy", None),
        ("anchor_buoyancy_aft_starboard", (1.8, -3.5, -0.35), "buoyancy", None),
        ("anchor_interaction", (0, 5.3, 1.2), "interaction", (0, 1, 0)),
    ]
    for name, location, role, forward in anchors:
        anchor(name, location, runtime, role, forward)
    add_preview_scene(preview, (20, -25, 14), (0, 0, 2.2), 28)
    return finish_asset(
        "east-blue-original-ship-proxy",
        runtime,
        preview,
        [item[0] for item in anchors],
        ["baratie-zoro-vs-mihawk"],
        "ocean-local-sector",
        "vehicle",
    )


def main() -> int:
    entries = [build_baratie_deck(), build_ship_proxy()]
    payload = {
        "schema_version": 1,
        "id": "grand-line-unreal-vertical-slice-assets-v1",
        "representation": "original-stylized-runtime-blockouts-with-authored-anchors",
        "ownership": {
            "blender": "reusable geometry and anchors",
            "unreal": "materials, collision, water, buoyancy, lighting, fx, and gameplay",
        },
        "assets": entries,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MANIFEST={MANIFEST}")
    for entry in entries:
        print(
            f"{entry['id']}: {entry['stats']['objects']} meshes, "
            f"{entry['stats']['anchors']} anchors, {entry['stats']['bytes']} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
