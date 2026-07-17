#!/usr/bin/env python3
"""Render a transparent runtime fallback from the currently-open .blend.

The source file is never saved. Optional collections can be hidden in-memory
to keep event actors out of a reusable base-state fallback.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resolution-x", type=int, default=1200)
    parser.add_argument("--resolution-y", type=int, default=900)
    parser.add_argument("--hide-collection", action="append", default=[])
    return parser.parse_args(argv)


def main() -> int:
    options = args()
    output = options.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for name in options.hide_collection:
        value = bpy.data.collections.get(name)
        if value is None:
            raise RuntimeError(f"Collection does not exist: {name}")
        value.hide_render = True
        value.hide_viewport = True
    for obj in bpy.context.scene.objects:
        if bool(obj.get("default_hidden", False)):
            obj.hide_render = True
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = options.resolution_x
    scene.render.resolution_y = options.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.render.filepath = str(output)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)
    print(f"FALLBACK={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
