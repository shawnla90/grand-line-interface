#!/usr/bin/env python3
"""Render an honest perspective preview of the currently opened Blender scene.

This does not save the .blend. It adds a temporary review camera and lights,
excludes preview ship/path helpers, frames the actual scene bounds, and writes
a PNG that makes vertical geometry visible.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--resolution-x", type=int, default=1400)
    parser.add_argument("--resolution-y", type=int, default=1000)
    return parser.parse_args(argv)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    args = arguments()
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    excluded_tokens = ("proxy", "runtime ship", "ascent path", "waterfall path")
    renderables = []
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            continue
        if any(token in obj.name.lower() for token in excluded_tokens):
            obj.hide_render = True
            continue
        if not obj.hide_render:
            renderables.append(obj)
    if not renderables:
        raise RuntimeError("No renderable scene geometry found")

    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    bounds_points: list[Vector] = []
    for obj in renderables:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            bounds_points.append(point)
            for axis in range(3):
                minimum[axis] = min(minimum[axis], point[axis])
                maximum[axis] = max(maximum[axis], point[axis])

    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    horizontal = max(extent.x, extent.y, 0.5)
    vertical = max(extent.z, 0.35)
    scene_scale = max(horizontal, vertical)
    scene = bpy.context.scene
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100

    camera_data = bpy.data.cameras.new("Perspective review camera")
    camera_data.lens = 56
    camera_data.sensor_width = 36
    camera_data.clip_start = max(0.01, scene_scale / 1000)
    camera_data.clip_end = scene_scale * 100
    camera = bpy.data.objects.new("Perspective review camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)

    # Plate-like scenes need a lower angle; vertical transitions need enough
    # height to show the entire climb while preserving a strong side view.
    if vertical > horizontal * 0.8:
        camera.location = center + Vector((scene_scale * 1.05, -scene_scale * 1.35, scene_scale * 0.62))
    else:
        camera.location = center + Vector((scene_scale * 0.95, -scene_scale * 1.25, scene_scale * 0.82))
    look_at(camera, center + Vector((0, 0, vertical * 0.02)))
    scene.camera = camera

    # Pull back until every actual geometry bound fits with a review margin.
    # A few bounded fit iterations are enough; an object with unusual flat
    # helper geometry must not push the useful scene into a tiny thumbnail.
    for _ in range(3):
        projected = [world_to_camera_view(scene, camera, point) for point in bounds_points]
        if (
            min(point.x for point in projected) >= 0.045
            and max(point.x for point in projected) <= 0.955
            and min(point.y for point in projected) >= 0.045
            and max(point.y for point in projected) <= 0.955
        ):
            break
        camera.location = center + (camera.location - center) * 1.16
        look_at(camera, center + Vector((0, 0, vertical * 0.02)))

    def area_light(name: str, location: Vector, energy: float, size: float, color: tuple[float, float, float]):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = center + location
        look_at(obj, center)

    area_light(
        "Perspective review key",
        Vector((-scene_scale * 0.8, -scene_scale * 0.6, scene_scale * 1.2)),
        1000 * max(1.0, scene_scale / 4),
        scene_scale * 0.8,
        (0.73, 0.87, 1.0),
    )
    area_light(
        "Perspective review rim",
        Vector((scene_scale * 0.9, scene_scale * 0.45, scene_scale * 0.75)),
        850 * max(1.0, scene_scale / 4),
        scene_scale * 0.6,
        (1.0, 0.63, 0.35),
    )

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(output)
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = 100
    scene.view_settings.look = "AgX - Medium High Contrast"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Perspective review world")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.004, 0.012, 0.022, 1.0)
    background.inputs["Strength"].default_value = 0.18

    bpy.ops.render.render(write_still=True)
    print(f"PERSPECTIVE={output}")
    print(
        "BOUNDS="
        f"({minimum.x:.3f},{minimum.y:.3f},{minimum.z:.3f}).."
        f"({maximum.x:.3f},{maximum.y:.3f},{maximum.z:.3f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
