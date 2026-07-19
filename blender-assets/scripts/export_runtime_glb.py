#!/usr/bin/env python3
"""Export the currently-open Blender scene as an optimized runtime GLB.

Usage:
  Blender --background source.blend --python scripts/export_runtime_glb.py -- \
    --id wano-waterfall-ascent --out runtime/wano-waterfall-ascent.glb

The source .blend is never saved. Curves are converted only in memory, cameras
and lights are excluded, and preview-only ship proxies are not exported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--animations", action="store_true",
                        help="Export named Blender Actions for chapter-sampled runtime motion")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def glb_header(path: Path) -> dict:
    with path.open("rb") as handle:
        magic, version, declared_length = struct.unpack("<4sII", handle.read(12))
    if magic != b"glTF" or version != 2 or declared_length != path.stat().st_size:
        raise RuntimeError(f"Invalid GLB header: {path}")
    return {"magic": "glTF", "version": version, "declared_length": declared_length}


def glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        handle.read(12)
        length, chunk_type = struct.unpack("<II", handle.read(8))
        if chunk_type != 0x4E4F534A:
            raise RuntimeError(f"GLB JSON chunk missing: {path}")
        return json.loads(handle.read(length).decode("utf-8").rstrip(" \t\r\n\x00"))


def main() -> int:
    args = cli_args()
    output = args.out.resolve()
    metadata = (args.metadata or output.with_suffix(".model.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)

    # Chapter-gated objects are commonly stored in hidden edit collections so
    # they stay out of review renders.  The GLB still needs those objects: their
    # custom properties become glTF node extras and let the runtime keep them
    # hidden until the gate is resolved.  This headless process is disposable,
    # so temporarily reveal only those collections before selecting/exporting.
    gated_objects = [
        obj for obj in bpy.context.scene.objects
        if bool(obj.get("default_hidden", False))
    ]
    for obj in gated_objects:
        obj.hide_viewport = False
        obj.hide_set(False)
        for owner in obj.users_collection:
            owner.hide_viewport = False

    excluded = []
    candidates = []
    for obj in list(bpy.context.scene.objects):
        preview_only = bool(obj.get("preview_only", False)) or "proxy" in obj.name.lower()
        gated = bool(obj.get("default_hidden", False))
        if obj.type not in {"MESH", "CURVE"} or preview_only or (not obj.visible_get() and not gated):
            excluded.append(obj.name)
            continue
        candidates.append(obj)

    # glTF has no native Blender Curve primitive. Convert curves to mesh only in
    # this disposable headless process; the editable .blend remains untouched.
    converted = []
    for obj in list(candidates):
        if obj.type != "CURVE":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        old_name = obj.name
        bpy.ops.object.convert(target="MESH")
        converted.append(old_name)

    export_objects = [obj for obj in bpy.context.scene.objects
                      if obj.type == "MESH" and not bool(obj.get("preview_only", False))
                      and "proxy" not in obj.name.lower()
                      and (obj.visible_get() or bool(obj.get("default_hidden", False)))]
    if not export_objects:
        raise RuntimeError("No renderable mesh objects found")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]

    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    vertex_count = 0
    triangle_count = 0
    materials = set()
    for obj in export_objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            minimum.x, minimum.y, minimum.z = min(minimum.x, world.x), min(minimum.y, world.y), min(minimum.z, world.z)
            maximum.x, maximum.y, maximum.z = max(maximum.x, world.x), max(maximum.y, world.y), max(maximum.z, world.z)
        vertex_count += len(obj.data.vertices)
        triangle_count += sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
        materials.update(slot.material.name for slot in obj.material_slots if slot.material)

    export_kwargs = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        # Applying animated object transforms destroys the hierarchy the clip
        # needs to move. Static blockouts retain the old baked-transform path.
        "export_apply": not args.animations,
        "export_animations": args.animations,
        "export_cameras": False,
        "export_lights": False,
        "export_extras": True,
        "export_yup": True,
        # Keep this export self-contained. Blender exposes the gltfpack option
        # even when no gltfpack binary is configured, which fails after all
        # geometry has been extracted. Runtime size is enforced by the
        # verification pass instead.
        "export_use_gltfpack": False,
        "export_image_format": "AUTO",
        "export_materials": "EXPORT",
        "check_existing": False,
    }
    if args.animations:
        export_kwargs.update({
            "export_animation_mode": "ACTIONS",
            "export_force_sampling": False,
            "export_optimize_animation_size": True,
            "export_optimize_animation_keep_anim_object": True,
        })
    bpy.ops.export_scene.gltf(**export_kwargs)
    header = glb_header(output)
    payload = glb_json(output)
    named_clips = []
    for animation in payload.get("animations", []):
        duration = 0.0
        for sampler in animation.get("samplers", []):
            accessor = payload["accessors"][sampler["input"]]
            duration = max(duration, float((accessor.get("max") or [0])[0]))
        named_clips.append({"name": animation.get("name"),
                            "duration_seconds": round(duration, 4)})
    report = {
        "schema_version": 1,
        "id": args.id,
        "source_blend": bpy.data.filepath,
        "runtime_glb": str(output),
        "model_units": "stylized Blender units; runtime scale is defined by the integration manifest",
        "coordinate_system": "glTF 2.0 Y-up; Blender exporter converts from Z-up",
        "export": {
            "exporter": "Blender built-in glTF 2.0 exporter",
            "compression": "none; optional gltfpack binary is not installed",
            "animations": args.animations,
            "animation_mode": "ACTIONS" if args.animations else None,
            "named_clips": named_clips,
            "preview_proxy_excluded": True,
            "curves_converted_to_mesh": converted,
            "excluded_objects": excluded,
        },
        "stats": {
            "objects": len(export_objects),
            "vertices_input": vertex_count,
            "triangles_input": triangle_count,
            "materials": len(materials),
            "bounds_blender": {
                "min": [round(minimum.x, 6), round(minimum.y, 6), round(minimum.z, 6)],
                "max": [round(maximum.x, 6), round(maximum.y, 6), round(maximum.z, 6)],
            },
            "bytes": output.stat().st_size,
        },
        "build": {
            "blender": bpy.app.version_string,
            "glb_sha256": sha256_file(output),
            "glb_header": header,
        },
    }
    metadata.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"GLB={output}")
    print(f"METADATA={metadata}")
    print(f"OBJECTS={len(export_objects)} VERTICES={vertex_count} TRIANGLES={triangle_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
