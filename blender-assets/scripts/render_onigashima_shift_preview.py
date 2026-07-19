#!/usr/bin/env python3
"""Render a short proof of the same Onigashima clip shipped in the GLB."""

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "previews/onigashima-geographic-shift"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    root = bpy.data.objects.get("Onigashima geographic root")
    action = bpy.data.actions.get("onigashima_geographic_shift")
    if root is None or action is None:
        raise RuntimeError("Onigashima root or geographic action missing")
    data = root.animation_data_create()
    data.use_nla = False
    data.action = action

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 680
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.compression = 35
    scene.render.fps = 8
    scene.world.color = (.008, .014, .028)

    flames = [obj for obj in scene.objects
              if obj.get("component_id") == "onigashima-flame-clouds"]
    samples = 40
    for index in range(samples):
        frame = round(1 + index * 139 / (samples - 1))
        # The preview uses the same verified state window as the runtime: flame
        # clouds appear after liftoff and disappear on safe landing.
        clouds_visible = 25 <= frame < 110
        for obj in flames:
            obj.hide_render = not clouds_visible
        scene.frame_set(frame)
        scene.render.filepath = str(OUT / f"frame-{index:03d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"PREVIEW {index+1:02d}/{samples} frame={frame}")


if __name__ == "__main__":
    main()
