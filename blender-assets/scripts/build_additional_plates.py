#!/usr/bin/env python3
"""Build Whole Cake Island, Impel Down, and Sabaody Blender plates.

The atlas repo is read-only. Current generated silhouette geometry is consumed
as the clipping contract, including Sabaody's MultiPolygon gaps.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fishman_plate import (
    Rng,
    curve_object,
    flat_polygon,
    make_collection,
    move_to_collection,
    principled_material,
    rgba,
    translucent_material,
)


ASSET_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = Path("/Users/shawnos.ai/dead-reckoning")
TARGETS = ("whole-cake-island", "impel-down", "sabaody-archipelago")
TAU = math.tau


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=2048)
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("DEAD_RECKONING_REPO", DEFAULT_REPO)))
    parser.add_argument("--only", action="append", choices=TARGETS,
                        help="Rebuild one plate; repeat to select multiple plates")
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


def polygon_area(ring: list[tuple[float, float]]) -> float:
    return abs(sum(ring[i][0] * ring[(i + 1) % len(ring)][1] -
                   ring[(i + 1) % len(ring)][0] * ring[i][1]
                   for i in range(len(ring))) / 2.0)


def ring_center(ring: list[tuple[float, float]]) -> tuple[float, float]:
    return (sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring))


def ring_extent(ring: list[tuple[float, float]]) -> tuple[float, float]:
    cx, cy = ring_center(ring)
    return max(abs(x - cx) for x, _ in ring), max(abs(y - cy) for _, y in ring)


def scaled_ring(ring: list[tuple[float, float]], scale: float) -> list[tuple[float, float]]:
    cx, cy = ring_center(ring)
    return [(cx + (x - cx) * scale, cy + (y - cy) * scale) for x, y in ring]


def point_in_ring_fraction(ring: list[tuple[float, float]], theta_index: int,
                           fraction: float) -> tuple[float, float]:
    cx, cy = ring_center(ring)
    x, y = ring[theta_index % len(ring)]
    return cx + (x - cx) * fraction, cy + (y - cy) * fraction


def load_contracts(repo: Path) -> dict[str, dict]:
    islands_path = repo / "data/generated/islands.json"
    coords_path = repo / "canon/islands.coords.json"
    silhouettes_path = repo / "public/geo/islands.silhouettes.json"
    voyage_path = repo / "canon/voyage_legs.json"
    islands = {item["slug"]: item for item in read_json(islands_path) if item["slug"] in TARGETS}
    coords = {item["slug"]: item for item in read_json(coords_path)["islands"] if item["slug"] in TARGETS}
    features = {feature["properties"]["slug"]: feature for feature in read_json(silhouettes_path)["features"]
                if feature["properties"]["slug"] in TARGETS}
    arrivals = {item["slug"]: item["chapter"] for item in read_json(voyage_path)["waypoints"]
                if item.get("slug") in TARGETS}

    contracts = {}
    for slug in TARGETS:
        feature = features[slug]
        geometry = feature["geometry"]
        coord = coords[slug]
        if geometry["type"] == "Polygon":
            geo_rings = [geometry["coordinates"][0][:-1]]
        elif geometry["type"] == "MultiPolygon":
            geo_rings = [polygon[0][:-1] for polygon in geometry["coordinates"]]
        else:
            raise ValueError(f"Unsupported geometry for {slug}: {geometry['type']}")
        local_rings = [[(lng - coord["lng"], lat - coord["lat"]) for lng, lat in ring]
                       for ring in geo_rings]
        contracts[slug] = {
            "slug": slug,
            "island": islands[slug],
            "coord": coord,
            "feature": feature,
            "geometry": geometry,
            "rings": local_rings,
            "biome": feature["properties"]["biome"],
            "arrival_chapter": arrivals.get(slug, islands[slug]["debut_chapter"]),
            "repo": repo,
            "input_paths": [islands_path, coords_path, silhouettes_path, voyage_path],
        }
    return contracts


def textured_material(name: str, dark: str, light: str, scale: float, roughness: float = 0.7):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.64
    ramp.color_ramp.elements[0].color = rgba(dark)
    ramp.color_ramp.elements[1].color = rgba(light)
    bsdf.inputs["Roughness"].default_value = roughness
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.09
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def add_cylinder(name: str, location: tuple[float, float, float], radius: float, depth: float,
                 material, collection, vertices: int = 48, scale_y: float = 1.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = scale_y
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    bevel = obj.modifiers.new("Soft edge", "BEVEL")
    bevel.width = min(radius * 0.12, depth * 0.2)
    bevel.segments = 3
    return obj


def add_sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
               material, collection, segments: int = 32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(12, segments // 2),
                                        location=location, scale=scale)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_cone(name: str, location: tuple[float, float, float], radius: float, depth: float,
             material, collection, vertices: int = 8):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=radius * 0.12,
                                    depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj


def add_ground(contract: dict, collection, material, coast_material,
               inner_material=None) -> None:
    for index, ring in enumerate(contract["rings"]):
        flat_polygon(f"{contract['slug']} exact footprint {index + 1}", ring, 0.0, collection, material)
        inner = scaled_ring(ring, 0.955)
        curve_object(f"Coastline {index + 1}", [(x, y, 0.035) for x, y in inner],
                     collection, coast_material, bevel=max(0.006, min(ring_extent(ring)) * 0.012), cyclic=True)
        if inner_material:
            flat_polygon(f"Interior wash {index + 1}", scaled_ring(ring, 0.90), 0.018,
                         collection, inner_material)


def build_whole_cake(contract: dict) -> None:
    ground = make_collection("01_Candy_Ground")
    cake = make_collection("02_Cake_Chateau")
    candy = make_collection("03_Candy_Forest")
    atmosphere = make_collection("04_Sugar_Sparkle")

    ground_mat = textured_material("M_Biscuit_Ground", "7b3b4d", "d88c8e", 3.8, 0.76)
    icing = principled_material("M_Strawberry_Icing", "f5a9c4", roughness=0.48,
                               emission="ffb6d0", emission_strength=0.14)
    cream = principled_material("M_Vanilla_Cream", "f5dfad", roughness=0.62)
    chocolate = principled_material("M_Dark_Chocolate", "3a1725", roughness=0.52, metallic=0.05)
    berry = principled_material("M_Berry_Candy", "b7246f", roughness=0.34,
                               emission="f94b9a", emission_strength=0.32)
    mint = principled_material("M_Mint_Candy", "5cd0ae", roughness=0.36,
                              emission="8cf5d6", emission_strength=0.25)
    gold = principled_material("M_Caramel_Gold", "e7a84d", roughness=0.40,
                              emission="ffc96a", emission_strength=0.28)
    coast = translucent_material("M_Sugar_Coast", "ffd7ea", 0.82, 3.2)
    sparkle = translucent_material("M_Sugar_Sparkle", "fff1c4", 0.72, 4.0)

    ring = max(contract["rings"], key=polygon_area)
    add_ground(contract, ground, ground_mat, coast, cream)
    cx, cy = ring_center(ring)
    rx, ry = ring_extent(ring)
    flat_polygon("Chocolate inner country", scaled_ring(ring, 0.68), 0.04, ground, chocolate)
    flat_polygon("Icing district", scaled_ring(ring, 0.48), 0.06, ground, icing)

    base_radius = min(rx, ry) * 0.33
    tier_specs = [
        (base_radius, 0.19, cream),
        (base_radius * 0.76, 0.18, icing),
        (base_radius * 0.52, 0.17, cream),
        (base_radius * 0.31, 0.15, berry),
    ]
    z = 0.12
    for index, (radius, depth, material) in enumerate(tier_specs):
        add_cylinder(f"Cake tier {index + 1}", (cx, cy, z + depth / 2), radius, depth,
                     material, cake, vertices=64, scale_y=0.88)
        z += depth * 0.82
    add_sphere("Chateau sugar crown", (cx, cy, z + 0.12),
               (base_radius * 0.22, base_radius * 0.18, 0.16), gold, cake)

    river_points = []
    for step in range(28):
        t = -0.72 + 1.44 * step / 27
        river_points.append((cx + rx * t, cy + ry * (0.18 * math.sin(t * 6.0) - 0.22), 0.09))
    curve_object("Chocolate river", river_points, ground, chocolate,
                 bevel=min(rx, ry) * 0.035)

    art_rng = Rng("blender:whole-cake-island:candy")
    candy_materials = [berry, mint, gold, cream]
    for index in range(52):
        vertex = int(art_rng.range(0, len(ring) - 0.001))
        fraction = art_rng.range(0.48, 0.84)
        x, y = point_in_ring_fraction(ring, vertex, fraction)
        radius = art_rng.range(0.025, 0.070) * min(rx, ry)
        add_sphere(f"Candy tree {index + 1:02d}", (x, y, 0.11 + radius * 0.7),
                   (radius, radius, radius * 1.15), candy_materials[index % len(candy_materials)], candy,
                   segments=24)
    for index in range(22):
        angle = TAU * index / 22 + art_rng.range(-0.08, 0.08)
        radius = art_rng.range(0.18, 0.44)
        x = cx + math.cos(angle) * rx * radius
        y = cy + math.sin(angle) * ry * radius
        add_sphere(f"Sugar light {index + 1:02d}", (x, y, 0.68),
                   (0.018, 0.018, 0.018), sparkle, atmosphere, segments=16)


def build_impel_down(contract: dict) -> None:
    ocean = make_collection("01_Calm_Belt_Abyss")
    levels = make_collection("02_Prison_Levels")
    chains = make_collection("03_Chain_Geometry")
    warning = make_collection("04_Red_Warning")

    abyss = textured_material("M_Abyss_Water", "050611", "182038", 4.8, 0.82)
    bruised = principled_material("M_Bruised_Stone", "29243b", roughness=0.78, metallic=0.12)
    iron = principled_material("M_Black_Iron", "11121b", roughness=0.36, metallic=0.72)
    bone = principled_material("M_Prison_Bone", "9aa0a5", roughness=0.62, metallic=0.25)
    red = principled_material("M_Inferno_Red", "8e1428", roughness=0.42,
                             emission="ff183d", emission_strength=2.8)
    deep_red = principled_material("M_Deep_Red", "3d0712", roughness=0.56,
                                  emission="9f0e26", emission_strength=1.3)
    coast = translucent_material("M_Abyss_Coast", "6574a8", 0.72, 2.0)
    chain_glow = translucent_material("M_Chain_Glint", "b7c5d9", 0.74, 2.8)

    ring = max(contract["rings"], key=polygon_area)
    add_ground(contract, ocean, abyss, coast, bruised)
    cx, cy = ring_center(ring)
    rx, ry = ring_extent(ring)
    for index, (scale, material) in enumerate(((0.78, iron), (0.64, bruised), (0.51, deep_red),
                                                (0.39, iron), (0.28, red), (0.17, iron))):
        flat_polygon(f"Submerged level {index + 1}", scaled_ring(ring, scale),
                     0.045 + index * 0.018, levels, material)

    tower_radius = min(rx, ry) * 0.16
    add_cylinder("Central prison shaft", (cx, cy, 0.34), tower_radius, 0.55, iron,
                 levels, vertices=12, scale_y=0.92)
    add_cylinder("Inferno core", (cx, cy, 0.64), tower_radius * 0.46, 0.14, red,
                 warning, vertices=12)
    for index in range(12):
        angle = TAU * index / 12
        x = cx + math.cos(angle) * tower_radius * 1.55
        y = cy + math.sin(angle) * tower_radius * 1.55
        add_cone(f"Prison spike {index + 1:02d}", (x, y, 0.35), tower_radius * 0.16,
                 0.42, bone if index % 2 else iron, levels, vertices=6)

    for index in range(10):
        target = point_in_ring_fraction(ring, int(index / 10 * len(ring)), 0.82)
        mid = (cx + (target[0] - cx) * 0.52,
               cy + (target[1] - cy) * 0.52 + math.sin(index * 1.7) * ry * 0.04,
               0.18)
        curve_object(f"Radial chain {index + 1:02d}",
                     [(cx, cy, 0.24), mid, (target[0], target[1], 0.11)], chains,
                     chain_glow, bevel=min(rx, ry) * 0.012)
    for index, scale in enumerate((0.84, 0.69, 0.54)):
        arc = [(x, y, 0.12 + index * 0.012) for x, y in scaled_ring(ring, scale)]
        curve_object(f"Containment ring {index + 1}", arc, chains,
                     chain_glow if index % 2 == 0 else red,
                     bevel=min(rx, ry) * (0.010 + index * 0.003), cyclic=True)


def build_sabaody(contract: dict) -> None:
    groves = make_collection("01_Mangrove_Groves")
    trees = make_collection("02_Resin_Mangroves")
    roots = make_collection("03_Root_Network")
    bubbles = make_collection("04_Resin_Bubbles")

    moss = textured_material("M_Grove_Moss", "133d37", "3b8a65", 5.2, 0.78)
    lagoon = principled_material("M_Lagoon_Wash", "3f8c83", roughness=0.60,
                                emission="62b5a8", emission_strength=0.08)
    bark = textured_material("M_Mangrove_Bark", "2b1b23", "754c38", 7.2, 0.88)
    canopy_dark = principled_material("M_Canopy_Dark", "1e5e48", roughness=0.72)
    canopy_light = principled_material("M_Canopy_Light", "6ea85d", roughness=0.68,
                                      emission="91c978", emission_strength=0.14)
    root_glow = translucent_material("M_Resin_Root_Glow", "4f9e75", 0.34, 1.4)
    bubble_glass = translucent_material("M_Resin_Bubble", "9fe8df", 0.16, glass=True)
    bubble_rose = translucent_material("M_Resin_Bubble_Rose", "f2a8d4", 0.15, glass=True)
    bubble_gold = translucent_material("M_Resin_Bubble_Gold", "f4d49b", 0.14, glass=True)
    bubble_rim = translucent_material("M_Resin_Bubble_Rim", "d5fff1", 0.78, 4.4)
    bubble_rim_rose = translucent_material("M_Resin_Bubble_Rim_Rose", "ffd1ed", 0.72, 4.0)
    bubble_rim_gold = translucent_material("M_Resin_Bubble_Rim_Gold", "ffe7b0", 0.70, 3.8)
    coast = translucent_material("M_Grove_Coast", "7dd6ae", 0.78, 2.8)

    add_ground(contract, groves, moss, coast, lagoon)
    art_rng = Rng("blender:sabaody-archipelago:groves")
    for grove_index, ring in enumerate(contract["rings"]):
        cx, cy = ring_center(ring)
        rx, ry = ring_extent(ring)
        small = min(rx, ry)
        trunk_radius = small * 0.12
        add_cylinder(f"Mangrove trunk {grove_index + 1}", (cx, cy, 0.33), trunk_radius,
                     0.64, bark, trees, vertices=18, scale_y=0.88)
        for canopy_index in range(9):
            angle = TAU * canopy_index / 9 + art_rng.range(-0.20, 0.20)
            spread = art_rng.range(0.05, 0.24)
            x = cx + math.cos(angle) * rx * spread
            y = cy + math.sin(angle) * ry * spread
            radius = art_rng.range(0.07, 0.14) * small
            add_sphere(f"Canopy {grove_index + 1}.{canopy_index + 1}", (x, y, 0.66),
                       (radius * 1.4, radius, radius * 0.72),
                       canopy_dark if canopy_index % 2 else canopy_light, trees, segments=24)
        for root_index in range(11):
            vertex = int(root_index / 11 * len(ring))
            end = point_in_ring_fraction(ring, vertex, 0.82)
            mid = (cx + (end[0] - cx) * 0.42 + art_rng.range(-0.04, 0.04) * rx,
                   cy + (end[1] - cy) * 0.42 + art_rng.range(-0.04, 0.04) * ry,
                   0.08)
            curve_object(f"Root {grove_index + 1}.{root_index + 1}",
                         [(cx, cy, 0.18), mid, (end[0], end[1], 0.06)], roots,
                         bark if root_index % 5 else root_glow,
                         bevel=small * art_rng.range(0.012, 0.026))
        bubble_materials = [bubble_glass, bubble_rose, bubble_gold]
        rim_materials = [bubble_rim, bubble_rim_rose, bubble_rim_gold]
        for bubble_index in range(16):
            vertex = int(art_rng.range(0, len(ring) - 0.001))
            x, y = point_in_ring_fraction(ring, vertex, art_rng.range(0.12, 0.50))
            radius = art_rng.range(0.055, 0.115) * small
            z = art_rng.range(0.36, 0.88)
            add_sphere(f"Resin bubble {grove_index + 1}.{bubble_index + 1}", (x, y, z),
                       (radius, radius, radius), bubble_materials[bubble_index % 3], bubbles, segments=28)
            if bubble_index % 2 == 0:
                arc = []
                for step in range(28):
                    theta = TAU * step / 27
                    arc.append((x + math.cos(theta) * radius * 0.92,
                                y + math.sin(theta) * radius * 0.92, z + radius * 0.18))
                curve_object(f"Bubble rim {grove_index + 1}.{bubble_index + 1}", arc,
                             bubbles, rim_materials[bubble_index % 3],
                             bevel=max(0.0035, radius * 0.075), cyclic=True)


BUILDERS = {
    "whole-cake-island": build_whole_cake,
    "impel-down": build_impel_down,
    "sabaody-archipelago": build_sabaody,
}


def setup_render(contract: dict, resolution: int) -> float:
    scene = bpy.context.scene
    all_points = [point for ring in contract["rings"] for point in ring]
    half_span = max(max(abs(x) for x, _ in all_points), max(abs(y) for _, y in all_points)) * 1.15

    camera_data = bpy.data.cameras.new("Top-down plate camera")
    camera = bpy.data.objects.new("Top-down plate camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 12.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = half_span * 2.0
    scene.camera = camera

    key_data = bpy.data.lights.new("Plate key", "AREA")
    key_data.energy = 680.0 if contract["slug"] != "impel-down" else 420.0
    key_data.color = (0.62, 0.82, 1.0) if contract["slug"] == "impel-down" else (1.0, 0.82, 0.62)
    key_data.shape = "DISK"
    key_data.size = 4.0
    key = bpy.data.objects.new("Plate key", key_data)
    scene.collection.objects.link(key)
    key.location = (-2.5, 2.2, 6.5)

    fill_data = bpy.data.lights.new("Plate fill", "POINT")
    fill_data.energy = 220.0
    fill_data.color = (1.0, 0.18, 0.26) if contract["slug"] == "impel-down" else (0.46, 1.0, 0.84)
    fill_data.shadow_soft_size = 1.4
    fill = bpy.data.objects.new("Plate fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (0.0, 0.0, 2.0)

    world = bpy.data.worlds.new("Plate world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        rgba("02030a") if contract["slug"] == "impel-down" else rgba("061918")
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.14
    scene.world = world

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 25
    scene.render.dither_intensity = 0.0
    scene.render.film_transparent = True
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
    glare.threshold = 1.0
    glare.size = 7
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])
    return half_span


def render_plate(contract: dict, resolution: int) -> tuple[dict, dict]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    slug = contract["slug"]
    scene["asset_track"] = "Grand Line Interface island plates"
    scene["plate_id"] = slug
    scene["repo_is_read_only"] = True
    scene["silhouette_source"] = "public/geo/islands.silhouettes.json"
    BUILDERS[slug](contract)
    half_span = setup_render(contract, resolution)

    blend_path = ASSET_ROOT / f"source/{slug}.blend"
    png_path = ASSET_ROOT / f"renders/{slug}.png"
    preview_path = ASSET_ROOT / f"renders/{slug}-preview.png"
    geometry_path = ASSET_ROOT / f"geometry/{slug}-coastline.geojson"
    scene.render.filepath = str(png_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    subprocess.run(["sips", "-Z", "768", str(png_path), "--out", str(preview_path)],
                   check=True, stdout=subprocess.DEVNULL)

    geojson = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/build_additional_plates.py",
            "source": "dead-reckoning/public/geo/islands.silhouettes.json",
            "geometry_type": contract["geometry"]["type"],
            "alpha_contract": "the production raster is opaque only inside this geometry",
        },
        "features": [{
            "type": "Feature",
            "properties": contract["feature"]["properties"],
            "geometry": contract["geometry"],
        }],
    }
    geometry_path.write_text(json.dumps(geojson, indent=2) + "\n", encoding="utf-8")

    lng, lat = contract["coord"]["lng"], contract["coord"]["lat"]
    coordinates = [
        [round(lng - half_span, 6), round(lat + half_span, 6)],
        [round(lng + half_span, 6), round(lat + half_span, 6)],
        [round(lng + half_span, 6), round(lat - half_span, 6)],
        [round(lng - half_span, 6), round(lat - half_span, 6)],
    ]
    art_directions = {
        "whole-cake-island": ["layered cake terrain", "chocolate river", "candy forest",
                              "strawberry icing districts", "warm sugar sparkle"],
        "impel-down": ["submerged concentric prison levels", "black iron shaft", "radial chains",
                       "inferno core", "Calm Belt abyss"],
        "sabaody-archipelago": ["three exact grove polygons", "resin mangroves", "root networks",
                               "floating bubbles", "lagoon-green light"],
    }
    build = {
        "blender": bpy.app.version_string,
        "script": "scripts/build_additional_plates.py",
        "raster_sha256": sha256_file(png_path),
        "preview_sha256": sha256_file(preview_path),
        "blend_sha256": sha256_file(blend_path),
        "geometry_sha256": sha256_file(geometry_path),
    }
    entry = {
        "id": slug,
        "label": f"{contract['island']['name']} — Blender plate",
        "source_blend": str(blend_path.relative_to(ASSET_ROOT)),
        "raster": str(png_path.relative_to(ASSET_ROOT)),
        "preview": str(preview_path.relative_to(ASSET_ROOT)),
        "coastline": str(geometry_path.relative_to(ASSET_ROOT)),
        "projection": "MapLibre image source coordinates, equirectangular",
        "coordinates": coordinates,
        "center": [lng, lat],
        "pixel_size": [resolution, resolution],
        "alpha_contract": f"opaque only inside the current {contract['geometry']['type']} silhouette",
        "coastline_contract": {
            "source": "public/geo/islands.silhouettes.json",
            "geometry_type": contract["geometry"]["type"],
            "polygon_count": len(contract["rings"]),
            "points_per_polygon": [len(ring) for ring in contract["rings"]],
            "biome": contract["biome"],
        },
        "spoiler_gate": {
            "debut_chapter": contract["island"]["debut_chapter"],
            "route_arrival_chapter": contract["arrival_chapter"],
        },
        "art_direction": art_directions[slug],
        "build": build,
    }
    source = {
        "input_sha256": {str(path.relative_to(contract["repo"])): sha256_file(path)
                          for path in contract["input_paths"]},
    }
    return entry, source


def merge_manifest(entries: list[dict], sources: dict, repo: Path, selected: tuple[str, ...]) -> None:
    manifest_path = ASSET_ROOT / "manifests/island-plates.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {
        "schema_version": 1,
        "integration_status": "asset-only; atlas currently has no plate-loading layer",
        "repo_write_contract": "read-only",
        "plates": [],
    }
    replacing = {entry["id"] for entry in entries}
    manifest["plates"] = [plate for plate in manifest.get("plates", []) if plate["id"] not in replacing] + entries
    try:
        repo_head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        repo_head = None
    manifest["additional_batch"] = {
        "script": "scripts/build_additional_plates.py",
        "blender": bpy.app.version_string,
        "git_head_at_build": repo_head,
        "plates": list(selected),
    }
    manifest.setdefault("sources_by_plate", {}).update(sources)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = cli_args()
    repo = args.repo.resolve()
    for directory in (ASSET_ROOT / "source", ASSET_ROOT / "renders", ASSET_ROOT / "manifests",
                      ASSET_ROOT / "geometry", ASSET_ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)
    contracts = load_contracts(repo)
    selected = tuple(args.only or TARGETS)
    entries = []
    sources = {}
    for slug in selected:
        entry, source = render_plate(contracts[slug], args.resolution)
        entries.append(entry)
        sources[slug] = source
        print(f"PLATE={ASSET_ROOT / entry['raster']}")
    merge_manifest(entries, sources, repo, selected)
    print(f"MANIFEST={ASSET_ROOT / 'manifests/island-plates.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
