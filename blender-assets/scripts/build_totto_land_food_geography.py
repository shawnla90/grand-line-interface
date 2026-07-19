#!/usr/bin/env python3
"""Build the additive Totto Land food-island geography package.

This deliberately does not replace the existing 34-island Totto Land blockout.
It supplies three close-readable geography theatres whose gates are already
present in local data: Whole Cake Island, Cacao Island, and Biscuits Island.
The only animated route is the ordinary open-sea path described in chapter
829. No juice river, chocolate river, or inland canal is claimed.

Run with Blender 4.5+:
  Blender --background --factory-startup --python \
    blender-assets/scripts/build_totto_land_food_geography.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "totto-land-food-geography"
SOURCE = ROOT / "source" / f"{ASSET_ID}.blend"
RENDER_DIR = ROOT / "renders" / "runtime"
MASTER_RENDER = RENDER_DIR / f"{ASSET_ID}.png"
FPS = 24


def collection(name: str) -> bpy.types.Collection:
    value = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(value)
    return value


def move(obj: bpy.types.Object, target: bpy.types.Collection) -> bpy.types.Object:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def hex_rgb(value: str) -> tuple[float, float, float]:
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def material(
    name: str,
    color: str,
    *,
    roughness: float = 0.68,
    metallic: float = 0.0,
    emission: str | None = None,
    emission_strength: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*hex_rgb(color), alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*hex_rgb(emission), 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        value.surface_render_method = "DITHERED"
    return value


def tag(
    obj: bpy.types.Object,
    component: str,
    reveal: int,
    *,
    gate_confidence: str = "verified",
    visual_status: str = "verified_identity_visual_interpolation",
    default_hidden: bool = False,
    active_through_chapter: float | None = None,
) -> bpy.types.Object:
    obj["component_id"] = component
    obj["reveal_chapter"] = reveal
    obj["gate_confidence"] = gate_confidence
    obj["default_hidden"] = default_hidden
    obj["visual_status"] = visual_status
    if active_through_chapter is not None:
        obj["active_through_chapter"] = active_through_chapter
    return obj


def bevel(obj: bpy.types.Object, width: float = 0.08, segments: int = 2) -> bpy.types.Object:
    modifier = obj.modifiers.new("Geography bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def cube(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    rotation_z: float = 0.0,
    visual_status: str = "verified_identity_visual_interpolation",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=(0.0, 0.0, rotation_z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, min(scale) * 0.14, 2)
    move(obj, target)
    return tag(obj, component, reveal, visual_status=visual_status)


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    vertices: int = 48,
    scale_xy: tuple[float, float] = (1.0, 1.0),
    visual_status: str = "verified_identity_visual_interpolation",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale.x, obj.scale.y = scale_xy
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, min(radius * 0.035, depth * 0.12), 2)
    move(obj, target)
    return tag(obj, component, reveal, visual_status=visual_status)


def cone(
    name: str,
    location: tuple[float, float, float],
    radius1: float,
    radius2: float,
    depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    vertices: int = 32,
    visual_status: str = "verified_identity_visual_interpolation",
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
    bevel(obj, radius1 * 0.025, 2)
    move(obj, target)
    return tag(obj, component, reveal, visual_status=visual_status)


def sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    segments: int = 24,
    rings: int = 14,
    visual_status: str = "verified_identity_visual_interpolation",
    gate_confidence: str = "verified",
    default_hidden: bool = False,
    active_through_chapter: float | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move(obj, target)
    return tag(
        obj,
        component,
        reveal,
        gate_confidence=gate_confidence,
        visual_status=visual_status,
        default_hidden=default_hidden,
        active_through_chapter=active_through_chapter,
    )


def torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    visual_status: str = "verified_identity_visual_interpolation",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=48,
        minor_segments=12,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move(obj, target)
    return tag(obj, component, reveal, visual_status=visual_status)


def curve(
    name: str,
    points: list[tuple[float, float, float]],
    bevel_depth: float,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    cyclic: bool = False,
    visual_status: str = "verified_identity_visual_interpolation",
    gate_confidence: str = "verified",
    default_hidden: bool = False,
    active_through_chapter: float | None = None,
) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    spline.use_cyclic_u = cyclic
    for handle, coordinate in zip(spline.bezier_points, points):
        handle.co = coordinate
        handle.handle_left_type = "AUTO"
        handle.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    obj.data.materials.append(mat)
    target.objects.link(obj)
    return tag(
        obj,
        component,
        reveal,
        gate_confidence=gate_confidence,
        visual_status=visual_status,
        default_hidden=default_hidden,
        active_through_chapter=active_through_chapter,
    )


def irregular_island(
    name: str,
    center: tuple[float, float, float],
    radii: tuple[float, float],
    depth: float,
    seed: int,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
    *,
    points: int = 48,
    visual_status: str = "verified_identity_visual_interpolation",
) -> bpy.types.Object:
    rng = random.Random(seed)
    cx, cy, cz = center
    verts: list[tuple[float, float, float]] = []
    top_shape: list[tuple[float, float]] = []
    for index in range(points):
        angle = math.tau * index / points
        wobble = 1.0 + rng.uniform(-0.12, 0.12) + math.sin(angle * 3 + seed) * 0.035
        top_shape.append((math.cos(angle) * radii[0] * wobble, math.sin(angle) * radii[1] * wobble))
    for x, y in top_shape:
        verts.append((cx + x, cy + y, cz + depth / 2))
    for x, y in top_shape:
        verts.append((cx + x * 0.92, cy + y * 0.92, cz - depth / 2))
    faces = [tuple(range(points)), tuple(range(points, points * 2))[::-1]]
    for index in range(points):
        nxt = (index + 1) % points
        faces.append((index, nxt, points + nxt, points + index))
    mesh = bpy.data.meshes.new(f"{name} mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    target.objects.link(obj)
    bevel(obj, 0.12, 3)
    return tag(obj, component, reveal, visual_status=visual_status)


def candy_house(
    prefix: str,
    location: tuple[float, float, float],
    size: float,
    wall: bpy.types.Material,
    roof: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
) -> None:
    x, y, z = location
    cube(
        f"{prefix} edible house",
        (x, y, z + size * 0.45),
        (size * 0.42, size * 0.34, size * 0.45),
        wall,
        target,
        component,
        reveal,
        rotation_z=(x + y) * 0.04,
    )
    cone(
        f"{prefix} frosting roof",
        (x, y, z + size * 1.02),
        size * 0.57,
        size * 0.08,
        size * 0.44,
        roof,
        target,
        component,
        reveal,
        vertices=8,
    )


def lollipop_tree(
    prefix: str,
    location: tuple[float, float, float],
    size: float,
    trunk_mat: bpy.types.Material,
    crown_mat: bpy.types.Material,
    target: bpy.types.Collection,
    component: str,
    reveal: int,
) -> None:
    x, y, z = location
    cylinder(
        f"{prefix} striped trunk",
        (x, y, z + size * 0.5),
        size * 0.09,
        size,
        trunk_mat,
        target,
        component,
        reveal,
        vertices=12,
    )
    sphere(
        f"{prefix} living crown",
        (x, y, z + size * 1.15),
        (size * 0.43, size * 0.36, size * 0.5),
        crown_mat,
        target,
        component,
        reveal,
        segments=18,
        rings=10,
    )


def build_whole_cake(
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> None:
    center = (1.5, 1.1)
    irregular_island(
        "Whole Cake Island hero coast",
        (center[0], center[1], 0.25),
        (6.4, 5.0),
        1.05,
        651,
        mats["wafer"],
        collections["whole"],
        "whole-cake-island",
        651,
    )
    tiers = (
        (4.05, 1.0, mats["sponge"]),
        (3.35, 1.63, mats["cream"]),
        (2.68, 2.22, mats["strawberry"]),
        (2.0, 2.78, mats["cream"]),
    )
    for index, (radius, z, mat) in enumerate(tiers):
        cylinder(
            f"Whole Cake sculpted tier {index + 1}",
            (center[0], center[1], z),
            radius,
            0.58,
            mat,
            collections["whole"],
            "whole-cake-island",
            651,
            vertices=64,
            scale_xy=(1.0, 0.84),
        )
    torus(
        "Whole Cake frosting garland",
        (center[0], center[1], 2.96),
        2.12,
        0.18,
        mats["icing"],
        collections["whole"],
        "whole-cake-island",
        651,
    )
    for index in range(18):
        angle = math.tau * index / 18
        sphere(
            f"Whole Cake icing drop {index + 1:02d}",
            (
                center[0] + math.cos(angle) * 2.12,
                center[1] + math.sin(angle) * 1.77,
                2.76 - 0.12 * (index % 3 == 0),
            ),
            (0.22, 0.18, 0.28),
            mats["icing"],
            collections["whole"],
            "whole-cake-island",
            651,
            segments=16,
            rings=8,
        )

    # Whole Cake Chateau: a readable cake-castle silhouette, not the generic box
    # used in the existing all-archipelago blockout.
    cube(
        "Whole Cake Chateau central keep",
        (center[0], center[1], 4.0),
        (0.92, 0.76, 0.92),
        mats["icing"],
        collections["whole"],
        "whole-cake-chateau",
        651,
    )
    for index, angle in enumerate((0.0, math.pi / 2, math.pi, math.pi * 1.5)):
        x = center[0] + math.cos(angle) * 1.18
        y = center[1] + math.sin(angle) * 0.96
        cylinder(
            f"Whole Cake Chateau tower {index + 1}",
            (x, y, 4.0),
            0.45,
            1.7,
            mats["cream"],
            collections["whole"],
            "whole-cake-chateau",
            651,
            vertices=20,
        )
        cone(
            f"Whole Cake Chateau sugar roof {index + 1}",
            (x, y, 5.05),
            0.64,
            0.03,
            0.7,
            mats["berry"],
            collections["whole"],
            "whole-cake-chateau",
            651,
            vertices=20,
        )
    cone(
        "Whole Cake Chateau crown roof",
        (center[0], center[1], 5.22),
        1.15,
        0.06,
        0.88,
        mats["gold"],
        collections["whole"],
        "whole-cake-chateau",
        651,
        vertices=24,
    )

    # Sweet City is explicitly named by the chapter-829 local summary. Its
    # exact street plan and building designs remain visual interpolation.
    for index in range(22):
        angle = math.tau * index / 22 + 0.12
        radius = 4.62 + (index % 3) * 0.28
        candy_house(
            f"Sweet City district {index + 1:02d}",
            (
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius * 0.77,
                0.77,
            ),
            0.48 + (index % 4) * 0.06,
            mats["candy_wall"] if index % 2 else mats["cream"],
            mats["berry"] if index % 3 else mats["gold"],
            collections["whole"],
            "sweet-city",
            829,
        )

    # The local chapter summary calls this the Forest of Temptation. The
    # commonly remembered Seducing Woods label is retained only as component
    # alias metadata in the contract/evidence ledger.
    for index in range(30):
        # Put the authored forest wedge on the review-facing coast so it remains
        # legible beside Sweet City. This bearing is presentation interpolation,
        # not a canon placement claim.
        row, column = divmod(index, 6)
        angle = -1.42 + column * 0.22 + row * 0.035
        radius = 4.45 + row * 0.29
        x = center[0] + math.cos(angle) * radius
        y = center[1] + math.sin(angle) * radius * 0.78
        lollipop_tree(
            f"Forest of Temptation tree {index + 1:02d}",
            (x, y, 0.8),
            0.66 + (index % 4) * 0.07,
            mats["chocolate"],
            mats["forest"] if index % 3 else mats["berry"],
            collections["whole"],
            "seducing-woods",
            831,
        )


def build_cacao(
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> None:
    center = (-9.4, -5.0)
    irregular_island(
        "Cacao Island whole-chocolate coast",
        (center[0], center[1], 0.28),
        (4.0, 3.0),
        1.12,
        827,
        mats["dark_chocolate"],
        collections["cacao"],
        "cacao-island",
        827,
        visual_status="verified_entirely_chocolate_visual_interpolation",
    )
    # Chocolate-bar terraces make the whole-island material premise visible.
    for row in range(4):
        for column in range(6):
            x = center[0] - 2.25 + column * 0.88 + (row % 2) * 0.12
            y = center[1] - 1.2 + row * 0.74
            height = 0.22 + 0.06 * ((row + column) % 3)
            cube(
                f"Cacao chocolate terrain tile {row + 1}-{column + 1}",
                (x, y, 0.94 + height / 2),
                (0.36, 0.28, height),
                mats["chocolate" if (row + column) % 2 else "milk_chocolate"],
                collections["cacao"],
                "cacao-island",
                827,
                rotation_z=0.04 * ((row + column) % 3 - 1),
                visual_status="verified_entirely_chocolate_visual_interpolation",
            )

    # The repository supports an edible chocolate settlement in chapter 827,
    # but not the remembered proper label "Chocolate Town". Use a neutral
    # component id and keep the exact street plan interpolated.
    for index in range(18):
        angle = math.tau * index / 18
        radius = 2.0 + (index % 3) * 0.34
        candy_house(
            f"Cacao chocolate settlement {index + 1:02d}",
            (
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius * 0.68,
                0.86,
            ),
            0.52 + (index % 4) * 0.06,
            mats["milk_chocolate"],
            mats["dark_chocolate" if index % 2 else "white_chocolate"],
            collections["cacao"],
            "cacao-chocolate-settlement",
            827,
        )
    # Pudding's home is established by the local summary, but its exact design
    # is not. A unique silhouette is therefore tagged visual interpolation.
    cylinder(
        "Pudding home chocolate roundhouse",
        (center[0] + 0.25, center[1] + 0.05, 1.55),
        0.72,
        1.15,
        mats["milk_chocolate"],
        collections["cacao"],
        "pudding-home-cacao",
        827,
        vertices=24,
    )
    cone(
        "Pudding home white chocolate roof",
        (center[0] + 0.25, center[1] + 0.05, 2.42),
        0.95,
        0.08,
        0.72,
        mats["white_chocolate"],
        collections["cacao"],
        "pudding-home-cacao",
        827,
        vertices=24,
    )
    for index in range(14):
        angle = math.tau * index / 14
        x = center[0] + math.cos(angle) * 3.2
        y = center[1] + math.sin(angle) * 2.35
        cylinder(
            f"Cacao tree trunk {index + 1:02d}",
            (x, y, 1.4),
            0.09,
            0.86,
            mats["dark_chocolate"],
            collections["cacao"],
            "cacao-island",
            827,
            vertices=10,
            visual_status="food_theme_visual_interpolation",
        )
        for pod in range(3):
            sphere(
                f"Cacao pod {index + 1:02d}-{pod + 1}",
                (x + (pod - 1) * 0.16, y, 1.85 + pod * 0.12),
                (0.14, 0.09, 0.24),
                mats["cacao_pod"],
                collections["cacao"],
                "cacao-island",
                827,
                segments=14,
                rings=8,
                visual_status="food_theme_visual_interpolation",
            )


def build_biscuits(
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> None:
    center = (-9.6, 6.0)
    irregular_island(
        "Biscuits Island hero coast",
        (center[0], center[1], 0.22),
        (3.8, 2.7),
        1.0,
        828,
        mats["biscuit"],
        collections["biscuits"],
        "biscuits-island",
        828,
        visual_status="verified_island_and_theme_visual_interpolation",
    )
    # Biscuit theme is locally directional-only. The terraces are a visual
    # family, not a claim that manga terrain has these exact cracker layers.
    for index, (radius, z) in enumerate(((3.25, 0.9), (2.55, 1.42), (1.8, 1.94))):
        cylinder(
            f"Biscuits Island cracker terrace {index + 1}",
            (center[0], center[1], z),
            radius,
            0.44,
            mats["biscuit" if index % 2 == 0 else "wafer"],
            collections["biscuits"],
            "biscuits-island",
            828,
            vertices=40,
            scale_xy=(1.0, 0.77),
            visual_status="verified_island_and_theme_visual_interpolation",
        )
    for index in range(34):
        angle = math.tau * index / 34
        radius = 2.82 if index % 2 else 2.2
        sphere(
            f"Biscuits Island perforation {index + 1:02d}",
            (
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius * 0.77,
                2.2 if index % 2 else 1.72,
            ),
            (0.095, 0.095, 0.055),
            mats["toasted"],
            collections["biscuits"],
            "biscuits-island",
            828,
            segments=12,
            rings=6,
            visual_status="food_theme_visual_interpolation",
        )
    for index in range(12):
        angle = math.tau * index / 12 + 0.15
        x = center[0] + math.cos(angle) * 1.4
        y = center[1] + math.sin(angle) * 1.0
        cube(
            f"Biscuits Island wafer tower {index + 1:02d}",
            (x, y, 2.35 + (index % 3) * 0.14),
            (0.34, 0.28, 0.52 + (index % 3) * 0.12),
            mats["wafer"],
            collections["biscuits"],
            "biscuits-island",
            828,
            rotation_z=angle + math.pi / 4,
            visual_status="food_theme_visual_interpolation",
        )
        cone(
            f"Biscuits Island wafer roof {index + 1:02d}",
            (x, y, 3.0 + (index % 3) * 0.25),
            0.48,
            0.08,
            0.35,
            mats["toasted"],
            collections["biscuits"],
            "biscuits-island",
            828,
            vertices=8,
            visual_status="food_theme_visual_interpolation",
        )


def build_route(
    collections: dict[str, bpy.types.Collection],
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    route_points = [
        (-7.4, -4.4, 0.42),
        (-5.2, -3.8, 0.47),
        (-2.8, -2.0, 0.45),
        (-0.4, -0.2, 0.44),
    ]
    route = curve(
        "Open sea route foam ribbon",
        route_points,
        0.085,
        mats["foam"],
        collections["route"],
        "totto-land-sea-route",
        829,
        visual_status="verified_sailing_route_visual_interpolation",
        gate_confidence="verified_state_window",
        default_hidden=True,
        active_through_chapter=829.999,
    )
    route["route_claim"] = "ordinary open sea path indicated by Pudding in chapter 829"
    route["not_a_claim"] = "not a juice river, chocolate river, canal, or exact canon bearing"
    route["clip:totto_land_food_route_cycle"] = "ambient_loop"

    # One neutral object-transform action gives the app an optional ambient
    # loop without baking movement into the islands or claiming a liquid river.
    base_location = route.location.copy()
    base_scale = route.scale.copy()
    animation = route.animation_data_create()
    animation.action = None
    for frame, z_offset, scale_y in ((1, 0.0, 1.0), (61, 0.08, 1.04), (121, 0.0, 1.0)):
        route.location = (base_location.x, base_location.y, base_location.z + z_offset)
        route.scale = (base_scale.x, base_scale.y * scale_y, base_scale.z)
        route.keyframe_insert(data_path="location", frame=frame)
        route.keyframe_insert(data_path="scale", frame=frame)
    action = animation.action
    if action is None:
        raise RuntimeError("Blender did not create the Totto Land route action")
    action.name = "totto_land_food_route_cycle"
    for fcurve in action.fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
    track = animation.nla_tracks.new()
    track.name = action.name
    strip = track.strips.new(action.name, int(action.frame_range[0]), action)
    strip.name = action.name
    animation.action = None
    animation.use_nla = False
    route.location = base_location
    route.scale = base_scale
    return route


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name: str, location: tuple[float, float, float], target: tuple[float, float, float], lens: float) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def area_light(name: str, location: tuple[float, float, float], energy: float, size: float, color: str) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = hex_rgb(color)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, (0.0, 0.0, 1.5))


def render_view(
    scene: bpy.types.Scene,
    cam: bpy.types.Object,
    path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    lens: float,
) -> None:
    cam.location = location
    cam.data.lens = lens
    look_at(cam, target)
    scene.camera = cam
    scene.render.filepath = str(path)
    scene.frame_set(1)
    bpy.ops.render.render(write_still=True)
    print(f"RENDER={path}")


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)

    collections = {
        "context": collection("00_CONTEXT"),
        "whole": collection("10_WHOLE_CAKE_GEOGRAPHY"),
        "cacao": collection("20_CACAO_GEOGRAPHY"),
        "biscuits": collection("30_BISCUITS_GEOGRAPHY"),
        "route": collection("40_OPEN_SEA_ROUTE"),
        "fx": collection("50_AMBIENT_FX"),
    }
    mats = {
        "ocean": material("M_Food_Geography_Ocean", "0d5772", roughness=0.2, metallic=0.05, alpha=0.9),
        "foam": material("M_Open_Sea_Foam", "dffcff", roughness=0.25, emission="9feeff", emission_strength=1.0),
        "wafer": material("M_Wafer_Coast", "b8783e", roughness=0.82),
        "sponge": material("M_Cake_Sponge_Hero", "e1ad62", roughness=0.72),
        "cream": material("M_Cake_Cream_Hero", "fff0cf", roughness=0.54),
        "icing": material("M_Icing_Hero", "fff9e9", roughness=0.46),
        "strawberry": material("M_Strawberry_Cake", "db7891", roughness=0.58),
        "berry": material("M_Berry_Glaze", "b52e55", roughness=0.38),
        "gold": material("M_Sugar_Gold_Hero", "e7bd57", roughness=0.35, metallic=0.28),
        "candy_wall": material("M_Sweet_City_Pastel", "d884aa", roughness=0.52),
        "forest": material("M_Forest_Of_Temptation", "52733d", roughness=0.75),
        "dark_chocolate": material("M_Dark_Chocolate_Coast", "361b17", roughness=0.74),
        "chocolate": material("M_Chocolate_Terrain", "5b2f22", roughness=0.68),
        "milk_chocolate": material("M_Milk_Chocolate", "8a5134", roughness=0.64),
        "white_chocolate": material("M_White_Chocolate", "f1d5a9", roughness=0.58),
        "cacao_pod": material("M_Cacao_Pod", "b96031", roughness=0.72),
        "biscuit": material("M_Biscuit_Terrain", "d39b50", roughness=0.84),
        "toasted": material("M_Toasted_Biscuit", "8d562f", roughness=0.86),
    }

    cylinder(
        "Totto Land food geography ocean stage",
        (-2.6, 0.3, -0.42),
        17.5,
        0.3,
        mats["ocean"],
        collections["context"],
        "totto-land-food-geography",
        651,
        vertices=96,
        scale_xy=(1.0, 0.72),
        visual_status="additive_local_theatre_not_canon_scale",
    )
    build_whole_cake(collections, mats)
    build_cacao(collections, mats)
    build_biscuits(collections, mats)
    build_route(collections, mats)

    # A few independent foam beads keep the open-sea connection legible at
    # globe-closeup LOD without turning it into a literal river.
    for index in range(12):
        t = index / 11
        x = -7.3 + t * 6.8
        y = -4.3 + t * 4.0 + math.sin(t * math.pi) * 0.45
        sphere(
            f"Open sea route foam bead {index + 1:02d}",
            (x, y, 0.46 + (index % 3) * 0.02),
            (0.12 + (index % 2) * 0.03, 0.08, 0.045),
            mats["foam"],
            collections["fx"],
            "totto-land-sea-route",
            829,
            segments=12,
            rings=6,
            visual_status="verified_sailing_route_visual_interpolation",
            gate_confidence="verified_state_window",
            default_hidden=True,
            active_through_chapter=829.999,
        )

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 121
    scene.render.fps = FPS
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1050
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 30
    scene.render.film_transparent = True
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world = bpy.data.worlds.new("Food Geography World")
    scene.world.color = (0.008, 0.012, 0.022)

    area_light("Food geography key", (2.0, -8.0, 20.0), 2600, 10.0, "ffd9b3")
    area_light("Food geography fill", (-15.0, -2.0, 11.0), 1700, 9.0, "8ddcff")
    area_light("Food geography rim", (7.0, 12.0, 16.0), 2100, 8.0, "f59bd5")
    cam = camera("Food Geography Camera", (24.0, -31.0, 26.0), (-2.8, 0.2, 1.7), 54.0)

    # Save before rendering so the source always contains the neutral frame-1
    # state and the NLA action, not a close-up camera left at another angle.
    scene.camera = cam
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)
    print(f"SOURCE={SOURCE}")

    render_view(scene, cam, MASTER_RENDER, (24.0, -31.0, 26.0), (-2.8, 0.2, 1.7), 54.0)
    render_view(
        scene,
        cam,
        RENDER_DIR / f"{ASSET_ID}-whole-cake.png",
        (13.5, -15.0, 13.2),
        (1.5, 1.1, 2.0),
        60.0,
    )
    render_view(
        scene,
        cam,
        RENDER_DIR / f"{ASSET_ID}-cacao.png",
        (-1.5, -17.5, 10.0),
        (-9.4, -5.0, 1.3),
        64.0,
    )
    render_view(
        scene,
        cam,
        RENDER_DIR / f"{ASSET_ID}-biscuits.png",
        (-2.0, -4.5, 11.2),
        (-9.6, 6.0, 1.5),
        64.0,
    )

    # Restore and save the master review camera as the default source view.
    cam.location = (24.0, -31.0, 26.0)
    cam.data.lens = 54.0
    look_at(cam, (-2.8, 0.2, 1.7))
    scene.camera = cam
    scene.render.filepath = str(MASTER_RENDER)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), check_existing=False)


if __name__ == "__main__":
    main()
