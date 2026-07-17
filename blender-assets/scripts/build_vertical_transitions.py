#!/usr/bin/env python3
"""Build animated-ready vertical transition sprites for Skypiea and Wano.

These are isolated Blender assets. The atlas repo is read-only and supplies
only current coordinates, silhouette geometry, and Skypiea's existing constants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_additional_plates import (  # noqa: E402
    Rng,
    add_cone,
    add_cylinder,
    add_sphere,
    curve_object,
    flat_polygon,
    make_collection,
    move_to_collection,
    polygon_area,
    principled_material,
    rgba,
    ring_center,
    scaled_ring,
    textured_material,
    translucent_material,
)


ASSET_ROOT = SCRIPT_DIR.parent
DEFAULT_REPO = Path("/Users/shawnos.ai/dead-reckoning")
TRANSITIONS = ("skypiea-knock-up-stream", "wano-waterfall-ascent")
TAU = math.tau


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-x", type=int, default=1024)
    parser.add_argument("--resolution-y", type=int, default=2048)
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("DEAD_RECKONING_REPO", DEFAULT_REPO)))
    parser.add_argument("--only", action="append", choices=TRANSITIONS)
    return parser.parse_args(argv)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(repo: Path) -> dict:
    islands_path = repo / "data/generated/islands.json"
    coords_path = repo / "canon/islands.coords.json"
    silhouettes_path = repo / "public/geo/islands.silhouettes.json"
    skypiea_module = repo / "components/skypiea.ts"
    islands = {item["slug"]: item for item in read_json(islands_path)
               if item["slug"] in {"skypiea", "wano-country"}}
    coords = {item["slug"]: item for item in read_json(coords_path)["islands"]
              if item["slug"] in {"skypiea", "wano-country"}}
    features = {feature["properties"]["slug"]: feature
                for feature in read_json(silhouettes_path)["features"]
                if feature["properties"]["slug"] in {"skypiea", "wano-country"}}

    def ring_for(slug: str):
        geometry = features[slug]["geometry"]
        if geometry["type"] != "Polygon":
            raise ValueError(f"{slug}: expected Polygon, got {geometry['type']}")
        return geometry["coordinates"][0][:-1]

    sky_ring_geo = ring_for("skypiea")
    wano_ring_geo = ring_for("wano-country")
    wano_south = min(wano_ring_geo, key=lambda point: point[1])
    wano_base = [round(wano_south[0], 4), round(wano_south[1] - 0.65, 4)]
    wano_crest = [round(wano_south[0], 4), round(wano_south[1] + 0.08, 4)]
    inputs = [islands_path, coords_path, silhouettes_path, skypiea_module]
    return {
        "repo": repo,
        "islands": islands,
        "coords": coords,
        "features": features,
        "sky_ring_geo": sky_ring_geo,
        "wano_ring_geo": wano_ring_geo,
        "wano_base": wano_base,
        "wano_crest": wano_crest,
        "inputs": inputs,
    }


def local_normalized_ring(geo_ring: list[list[float]], size: float) -> list[tuple[float, float]]:
    cx = sum(point[0] for point in geo_ring) / len(geo_ring)
    cy = sum(point[1] for point in geo_ring) / len(geo_ring)
    local = [(lng - cx, lat - cy) for lng, lat in geo_ring]
    extent = max(max(abs(x) for x, _ in local), max(abs(y) for _, y in local))
    return [(x / extent * size, y / extent * size) for x, y in local]


def ellipse_ring(rx: float, ry: float, cx: float = 0.0, cy: float = 0.0,
                 points: int = 96) -> list[tuple[float, float]]:
    return [(cx + math.cos(i / points * TAU) * rx,
             cy + math.sin(i / points * TAU) * ry) for i in range(points)]


def look_at(obj, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_tapered_column(name: str, z_bottom: float, z_top: float, radius_bottom: float,
                       radius_top: float, material, collection, vertices: int = 64):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius_bottom, radius2=radius_top,
                                    depth=z_top - z_bottom,
                                    location=(0.0, 0.0, (z_top + z_bottom) / 2.0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_proxy_ship(name: str, start: tuple[float, float, float],
                   end: tuple[float, float, float], collection, material):
    add_sphere(name, start, (0.16, 0.11, 0.10), material, collection, segments=24)
    obj = bpy.context.object
    obj.location = start
    obj.keyframe_insert(data_path="location", frame=1)
    obj.location = end
    obj.keyframe_insert(data_path="location", frame=100)
    obj.keyframe_insert(data_path="location", frame=120)
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
    obj["preview_only"] = True
    obj["runtime_owner"] = "existing atlas ship marker"
    return obj


def build_skypiea(contract: dict) -> dict:
    sea = make_collection("01_Sea_Base")
    stream = make_collection("02_Knock_Up_Stream")
    clouds = make_collection("03_Cloud_Platform")
    route = make_collection("04_Ascent_Reference")

    sea_mat = textured_material("M_Sea_Surface", "062b3a", "146d78", 4.2, 0.68)
    shadow_mat = principled_material("M_Cloud_Shadow", "07131d", roughness=0.92)
    water_outer = translucent_material("M_Stream_Outer", "59cfff", 0.22, 2.8)
    water_core = translucent_material("M_Stream_Core", "d1f8ff", 0.50, 5.0)
    foam = principled_material("M_Cloud_Foam", "e8f5f0", roughness=0.76,
                              emission="ffffff", emission_strength=0.18)
    cloud_blue = principled_material("M_Cloud_Blue", "a9dce3", roughness=0.72,
                                    emission="d9fbff", emission_strength=0.12)
    sky_land = textured_material("M_Sky_Land", "8c7b43", "c8b86d", 4.8, 0.74)
    tracer = translucent_material("M_Upward_Tracer", "ffffff", 0.82, 5.8)
    ship_gold = principled_material("M_Ship_Proxy", "f2bd54", roughness=0.30,
                                   emission="ffd66d", emission_strength=3.4)

    flat_polygon("Sea eruption footprint", ellipse_ring(1.75, 0.78, cy=-0.35), 0.0, sea, sea_mat)
    flat_polygon("Cloud shadow", ellipse_ring(1.10, 0.46, cy=-0.18), 0.035, sea, shadow_mat)
    add_tapered_column("Knock-Up Stream outer column", 0.16, 5.82, 0.58, 0.29,
                       water_outer, stream)
    add_tapered_column("Knock-Up Stream luminous core", 0.20, 5.90, 0.27, 0.14,
                       water_core, stream)

    art_rng = Rng("blender:skypiea:vertical-transition")
    for helix_index in range(5):
        points = []
        phase = helix_index / 5 * TAU
        for step in range(90):
            t = step / 89
            theta = phase + t * TAU * art_rng.range(1.4, 2.2)
            radius = (0.48 - 0.20 * t) * (0.78 + helix_index * 0.045)
            points.append((math.cos(theta) * radius,
                           math.sin(theta) * radius * 0.42,
                           0.24 + 5.52 * t))
        curve_object(f"Rising water helix {helix_index + 1}", points, stream,
                     water_core if helix_index % 2 == 0 else water_outer,
                     bevel=0.022 + helix_index * 0.003)

    for index in range(24):
        angle = index / 24 * TAU + art_rng.range(-0.12, 0.12)
        radius = art_rng.range(0.35, 1.28)
        x = math.cos(angle) * radius
        y = -0.30 + math.sin(angle) * radius * 0.42
        size = art_rng.range(0.06, 0.17)
        add_sphere(f"Base foam {index + 1:02d}", (x, y, art_rng.range(0.07, 0.24)),
                   (size * 1.4, size, size * 0.72), foam, sea, segments=24)

    sky_ring = local_normalized_ring(contract["sky_ring_geo"], 2.15)
    flat_polygon("Skypiea cloud shelf", sky_ring, 5.95, clouds, foam)
    flat_polygon("Skypiea land heart", scaled_ring(sky_ring, 0.56), 6.04, clouds, sky_land)
    for index in range(28):
        angle = index / 28 * TAU + art_rng.range(-0.18, 0.18)
        radius = art_rng.range(1.45, 2.05)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius * 0.55
        size = art_rng.range(0.16, 0.34)
        add_sphere(f"Cloud bank {index + 1:02d}", (x, y, 5.93 + art_rng.range(-0.06, 0.12)),
                   (size * 1.45, size, size * 0.62), foam if index % 3 else cloud_blue,
                   clouds, segments=28)

    tracer_points = [(0.0, -0.10 + 0.05 * math.sin(step * 0.55), 0.42 + 5.25 * step / 38)
                     for step in range(39)]
    curve_object("Runtime ship ascent path", tracer_points, route, tracer, bevel=0.045)
    proxy = add_proxy_ship("Ship ascent proxy", tracer_points[0], tracer_points[-1], route, ship_gold)
    proxy["chapter_start"] = 235
    proxy["chapter_top"] = 237
    return {
        "camera_target": (0.0, 0.0, 3.05),
        "camera_scale": 10.4,
        "preview_frame": 58,
        "art_direction": ["erupting vertical ocean column", "spiraling water helices",
                          "sea-level cloud shadow", "cloud shelf above", "upward route tracer"],
    }


def extruded_plateau(name: str, ring: list[tuple[float, float]], z_bottom: float, z_top: float,
                     side_material, top_material, collection):
    count = len(ring)
    bottom = [(x * 0.82, y * 0.82, z_bottom) for x, y in ring]
    top = [(x, y, z_top) for x, y in ring]
    vertices = bottom + top
    faces = [tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(f"G_{name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(top_material)
    obj.data.materials.append(side_material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0 if len(polygon.vertices) == count else 1
    return obj


def waterfall_ribbon(path: list[tuple[float, float, float]], widths: list[float], material,
                     collection, name: str):
    vertices = []
    for (x, y, z), width in zip(path, widths):
        vertices.extend([(x - width / 2, y, z), (x + width / 2, y, z)])
    faces = []
    for index in range(len(path) - 1):
        a = index * 2
        faces.append((a, a + 1, a + 3, a + 2))
    mesh = bpy.data.meshes.new(f"G_{name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def build_wano(contract: dict) -> dict:
    ocean = make_collection("01_New_World_Sea")
    cliff = make_collection("02_Raised_Wano_Plateau")
    falls = make_collection("03_Waterfall_Ascent")
    mist = make_collection("04_Waterfall_Mist")
    route = make_collection("05_Ascent_Reference")

    ocean_mat = textured_material("M_New_World_Sea", "06273b", "0c7181", 4.6, 0.70)
    cliff_mat = textured_material("M_Wano_Cliff", "332d38", "75615b", 6.5, 0.86)
    top_mat = textured_material("M_Wano_Top", "314f36", "77905b", 5.0, 0.78)
    dark_under = principled_material("M_Cliff_Underbelly", "15151f", roughness=0.94)
    water = translucent_material("M_Wano_Falls", "49c9e4", 0.38, 3.8)
    foam = principled_material("M_Wano_Foam", "dcefed", roughness=0.76,
                              emission="ffffff", emission_strength=0.24)
    tracer = translucent_material("M_Climb_Tracer", "ffe58c", 0.86, 6.0)
    ship_gold = principled_material("M_Wano_Ship_Proxy", "e7ad46", roughness=0.28,
                                   emission="ffd267", emission_strength=3.5)
    settlement = principled_material("M_Wano_Lanterns", "bf4c35", roughness=0.45,
                                    emission="ff6d42", emission_strength=1.6)

    flat_polygon("Sea below Wano", ellipse_ring(2.25, 0.90, cy=-1.0), 0.0, ocean, ocean_mat)
    wano_ring = local_normalized_ring(contract["wano_ring_geo"], 2.62)
    extruded_plateau("Raised Wano cliff body", wano_ring, 2.15, 5.30,
                     cliff_mat, dark_under, cliff)
    flat_polygon("Wano upper country", scaled_ring(wano_ring, 0.96), 5.34, cliff, top_mat)

    south_x, south_y = min(wano_ring, key=lambda point: point[1])
    path = []
    widths = []
    steps = 34
    for step in range(steps):
        t = step / (steps - 1)
        z = 0.32 + 4.98 * t
        y = south_y - 0.82 * (1.0 - t) + 0.03 * math.sin(t * math.pi * 2)
        x = south_x + 0.10 * math.sin(t * math.pi * 2.4)
        path.append((x, y, z))
        widths.append(0.86 - 0.28 * t)
    waterfall_ribbon(path, widths, water, falls, "Wano vertical waterfall")
    left_edge = [(x - width / 2, y - 0.012, z) for (x, y, z), width in zip(path, widths)]
    right_edge = [(x + width / 2, y - 0.012, z) for (x, y, z), width in zip(path, widths)]
    curve_object("Falls foam edge left", left_edge, falls, foam, bevel=0.038)
    curve_object("Falls foam edge right", right_edge, falls, foam, bevel=0.038)

    tracer_points = [(x, y - 0.028, z + 0.05) for x, y, z in path]
    curve_object("Runtime ship waterfall path", tracer_points, route, tracer, bevel=0.050)
    proxy = add_proxy_ship("Ship waterfall proxy", tracer_points[0], tracer_points[-1], route, ship_gold)
    proxy["chapter_contract"] = "proposed: arrival 909; exact climb beats need app-owner verification"

    art_rng = Rng("blender:wano:vertical-transition")
    for bank, base in (("base", path[0]), ("crest", path[-1])):
        count = 25 if bank == "base" else 17
        for index in range(count):
            angle = index / count * TAU + art_rng.range(-0.18, 0.18)
            radius = art_rng.range(0.18, 0.86 if bank == "base" else 0.58)
            size = art_rng.range(0.07, 0.20)
            add_sphere(f"{bank.title()} mist {index + 1:02d}",
                       (base[0] + math.cos(angle) * radius,
                        base[1] + math.sin(angle) * radius * 0.42,
                        base[2] + art_rng.range(-0.02, 0.28)),
                       (size * 1.5, size, size * 0.66), foam, mist, segments=24)

    cx, cy = ring_center(wano_ring)
    for index in range(13):
        angle = index / 13 * TAU
        radius = art_rng.range(0.35, 1.12)
        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius * 0.55
        add_cone(f"Wano lantern tower {index + 1:02d}", (x, y, 5.55), 0.055,
                 art_rng.range(0.20, 0.42), settlement, cliff, vertices=6)
    return {
        "camera_target": (0.0, -0.12, 3.0),
        "camera_scale": 11.8,
        "preview_frame": 58,
        "art_direction": ["raised cliff plateau", "visible dark understructure",
                          "vertical waterfall ribbon", "crest and base mist", "upward ship tracer"],
    }


BUILDERS = {
    "skypiea-knock-up-stream": build_skypiea,
    "wano-waterfall-ascent": build_wano,
}


def setup_render(meta: dict, resolution_x: int, resolution_y: int) -> None:
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Vertical transition camera")
    camera = bpy.data.objects.new("Vertical transition camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (8.2, -14.5, 8.2)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = meta["camera_scale"]
    look_at(camera, meta["camera_target"])
    scene.camera = camera

    key_data = bpy.data.lights.new("Vertical key", "AREA")
    key_data.energy = 820.0
    key_data.color = (0.55, 0.82, 1.0)
    key_data.shape = "DISK"
    key_data.size = 4.5
    key = bpy.data.objects.new("Vertical key", key_data)
    scene.collection.objects.link(key)
    key.location = (-3.5, -4.0, 10.0)
    look_at(key, meta["camera_target"])

    fill_data = bpy.data.lights.new("Vertical warm fill", "POINT")
    fill_data.energy = 300.0
    fill_data.color = (1.0, 0.46, 0.22)
    fill_data.shadow_soft_size = 1.4
    fill = bpy.data.objects.new("Vertical warm fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (2.0, -2.0, 5.2)

    world = bpy.data.worlds.new("Vertical transparent world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = rgba("020711")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.10
    scene.world = world

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 25
    scene.render.dither_intensity = 0.0
    scene.render.film_transparent = True
    scene.frame_start = 1
    scene.frame_end = 120
    scene.render.fps = 30
    scene.frame_set(meta["preview_frame"])
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 0.85
    glare.size = 7
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])


def skypiea_integration(contract: dict) -> dict:
    base = [-91.1362, 8.2]
    body = [-91.1362, 17.0745]
    south = base[1] - 0.9
    north = body[1] + 0.9
    height = north - south
    width = height * 0.5
    west, east = base[0] - width / 2, base[0] + width / 2
    return {
        "mode": "maplibre_image_source",
        "coordinates": [[round(west, 6), round(north, 6)], [round(east, 6), round(north, 6)],
                        [round(east, 6), round(south, 6)], [round(west, 6), round(south, 6)]],
        "source_anchor": base,
        "destination_anchor": body,
        "runtime_module": "components/skypiea.ts",
        "chapter_beats": {"start": 235, "top": 237, "dwellEnd": 300, "splash": 304},
        "runtime_rule": "opacity follows columnOpacity(ch); ship motion stays altitudeT(ch)",
    }


def wano_integration(contract: dict) -> dict:
    body = [contract["coords"]["wano-country"]["lng"], contract["coords"]["wano-country"]["lat"]]
    return {
        "mode": "screen_space_html_marker",
        "anchor": contract["wano_base"],
        "crest_anchor": contract["wano_crest"],
        "destination_anchor": body,
        "transform_origin": "50% 100%",
        "proposed_runtime_module": "components/wano.ts",
        "chapter_beats": {"arrival": 909, "start": None, "crest": None,
                          "status": "proposed; exact waterfall climb beats need human verification"},
        "runtime_rule": "sprite is pixel-space; real ship marker follows a pure climbT(ch) path",
    }


def render_transition(transition_id: str, contract: dict, resolution_x: int, resolution_y: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene["asset_track"] = "Grand Line Interface vertical transitions"
    scene["transition_id"] = transition_id
    scene["repo_is_read_only"] = True
    scene["runtime_ship_proxy_is_preview_only"] = True
    meta = BUILDERS[transition_id](contract)
    setup_render(meta, resolution_x, resolution_y)

    blend_path = ASSET_ROOT / f"source/{transition_id}.blend"
    png_path = ASSET_ROOT / f"renders/{transition_id}.png"
    preview_path = ASSET_ROOT / f"renders/{transition_id}-preview.png"
    scene.render.filepath = str(png_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    subprocess.run(["sips", "-Z", "768", str(png_path), "--out", str(preview_path)],
                   check=True, stdout=subprocess.DEVNULL)

    integration = skypiea_integration(contract) if transition_id.startswith("skypiea") else wano_integration(contract)
    entry = {
        "id": transition_id,
        "label": "Skypiea — Knock-Up Stream" if transition_id.startswith("skypiea") else "Wano — waterfall ascent",
        "source_blend": str(blend_path.relative_to(ASSET_ROOT)),
        "raster": str(png_path.relative_to(ASSET_ROOT)),
        "preview": str(preview_path.relative_to(ASSET_ROOT)),
        "pixel_size": [resolution_x, resolution_y],
        "alpha_contract": "transparent portrait sprite; no geographic coastline clipping",
        "animation_reference": {
            "frames": [1, 120],
            "fps": 30,
            "preview_frame": meta["preview_frame"],
            "proxy_note": "Blender proxy demonstrates direction only; runtime ship marker owns motion",
        },
        "art_direction": meta["art_direction"],
        "integration": integration,
        "build": {
            "blender": bpy.app.version_string,
            "script": "scripts/build_vertical_transitions.py",
            "raster_sha256": sha256_file(png_path),
            "preview_sha256": sha256_file(preview_path),
            "blend_sha256": sha256_file(blend_path),
        },
    }
    return entry


def main() -> int:
    args = cli_args()
    repo = args.repo.resolve()
    contract = load_contract(repo)
    selected = tuple(args.only or TRANSITIONS)
    entries = [render_transition(item, contract, args.resolution_x, args.resolution_y) for item in selected]
    manifest_path = ASSET_ROOT / "manifests/vertical-transitions.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {
        "schema_version": 1,
        "asset_class": "vertical-transition-sprite",
        "integration_status": "asset-only; no transition loader is written by this track",
        "repo_write_contract": "read-only",
        "transitions": [],
    }
    replacing = {entry["id"] for entry in entries}
    manifest["transitions"] = [entry for entry in manifest.get("transitions", [])
                               if entry["id"] not in replacing] + entries
    try:
        repo_head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        repo_head = None
    manifest["source"] = {
        "repo": str(repo),
        "git_head_at_build": repo_head,
        "input_sha256": {str(path.relative_to(repo)): sha256_file(path) for path in contract["inputs"]},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for entry in entries:
        print(f"TRANSITION={ASSET_ROOT / entry['raster']}")
    print(f"MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
