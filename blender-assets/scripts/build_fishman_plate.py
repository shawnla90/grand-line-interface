#!/usr/bin/env python3
"""Build the Fish-Man Island Blender plate without writing to the atlas repo.

Run with Blender, not system Python:
  Blender --background --python scripts/build_fishman_plate.py -- --resolution 2048

The atlas repo is an input only. This script deliberately reimplements the
small deterministic coastline contract instead of importing atlas modules,
because importing them could create __pycache__ files inside the live repo.
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


TAU = 2.0 * math.pi
SLUG = "fish-man-island"
COAST_POINTS = 128
DEFAULT_REPO = Path("/Users/shawnos.ai/dead-reckoning")
ASSET_ROOT = Path(__file__).resolve().parent.parent


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=2048)
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("DEAD_RECKONING_REPO", DEFAULT_REPO)))
    return parser.parse_args(argv)


class Rng:
    """The atlas sha256 counter stream, reproduced exactly."""

    def __init__(self, seed: str):
        self.seed = seed.encode()
        self.n = 0

    def unit(self) -> float:
        digest = hashlib.sha256(self.seed + self.n.to_bytes(4, "big")).hexdigest()
        self.n += 1
        return int(digest[:8], 16) / 0xFFFFFFFF

    def range(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.unit()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def coastline_contract(repo: Path) -> dict:
    island_path = repo / "data/generated/islands.json"
    coords_path = repo / "canon/islands.coords.json"
    voyage_path = repo / "canon/voyage_legs.json"
    presence_path = repo / "canon/crew_presence.json"
    biome_path = repo / "canon/islands.biomes.json"

    island = next(item for item in read_json(island_path) if item["slug"] == SLUG)
    coord = next(item for item in read_json(coords_path)["islands"] if item["slug"] == SLUG)
    voyage = read_json(voyage_path)
    presence = read_json(presence_path)
    overrides = read_json(biome_path).get("biomes", {})

    voyage_slugs = {item.get("slug") for item in voyage["waypoints"] if item.get("slug")}
    anchor_slugs = {
        window["island_slug"]
        for entity in presence.get("crews", []) + presence.get("characters", [])
        for window in entity.get("windows", [])
        if window.get("island_slug")
    }

    # biomes.py resolution, reduced to the Fish-Man Island inputs.
    biome = overrides.get(SLUG)
    if not biome:
        island_type = (island.get("island_type") or "").lower()
        type_map = [("winter", "winter"), ("summer", "summer"), ("prehistoric", "jungle"),
                    ("desert", "desert"), ("sky", "sky")]
        biome = next((value for needle, value in type_map if needle in island_type), None)
    if not biome and (coord.get("sea") or island.get("sea")) == "Sky":
        biome = "sky"
    if not biome:
        name = island["name"].lower()
        keyword_map = [(("desert", "sand", "dune"), "desert"),
                       (("snow", "ice", "winter"), "winter"),
                       (("volcan", "hazard"), "volcanic"),
                       (("sky", "cloud", "heaven"), "sky"),
                       (("jungle",), "jungle")]
        biome = next((value for needles, value in keyword_map if any(n in name for n in needles)), "temperate")

    profiles = {
        "sky": ([(2, 0.16), (3, 0.10)], 0.0),
        "winter": ([(3, 0.14), (7, 0.12), (11, 0.08)], 0.06),
        "summer": ([(2, 0.14), (5, 0.10)], 0.0),
        "desert": ([(2, 0.12), (3, 0.07)], 0.10),
        "volcanic": ([(3, 0.13), (6, 0.09)], 0.05),
        "jungle": ([(2, 0.13), (5, 0.11), (9, 0.06)], 0.04),
        "temperate": ([(2, 0.13), (4, 0.10), (7, 0.07)], 0.03),
    }
    freqs, spike = profiles[biome]

    rng = Rng(f"silhouette:{SLUG}")
    if SLUG in voyage_slugs:
        radius = rng.range(1.40, 1.95)
        weight = "voyage"
    elif SLUG in anchor_slugs:
        radius = rng.range(1.00, 1.45)
        weight = "presence"
    else:
        radius = rng.range(0.50, 0.95)
        weight = "background"

    # data/generated/islands.json has sea=null for FMI, so geometry_for draws
    # this elongation from the stream instead of taking the Grand Line constant.
    elong = 1.25 if island.get("sea") == "Grand Line" else rng.range(0.9, 1.15)
    phases = [rng.range(0, TAU) for _ in freqs]
    spike_at = rng.range(0, TAU)

    def radial_factor(theta: float) -> float:
        value = 1.0
        for (frequency, amplitude), phase in zip(freqs, phases):
            value += amplitude * math.sin(frequency * theta + phase)
        if spike:
            value += spike * max(0.0, math.cos(theta - spike_at)) ** 3
        return max(0.35, value)

    r_lng = radius * elong
    r_lat = radius / elong
    ring_local = []
    ring_geo = []
    for index in range(COAST_POINTS):
        theta = index / COAST_POINTS * TAU
        factor = radial_factor(theta)
        x = math.cos(theta) * r_lng * factor
        y = math.sin(theta) * r_lat * factor
        ring_local.append((x, y))
        ring_geo.append((round(coord["lng"] + x, 4), round(coord["lat"] + y, 4)))

    return {
        "island": island,
        "coord": coord,
        "biome": biome,
        "weight": weight,
        "radius": radius,
        "elong": elong,
        "r_lng": r_lng,
        "r_lat": r_lat,
        "radial_factor": radial_factor,
        "ring_local": ring_local,
        "ring_geo": ring_geo,
        "inputs": [island_path, coords_path, voyage_path, presence_path, biome_path,
                   repo / "scripts/gen_silhouettes.py", repo / "scripts/gen_terrain.py"],
    }


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def make_collection(name: str):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    color = hex_color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)


def principled_material(name: str, color: str, *, roughness: float = 0.55,
                        metallic: float = 0.0, emission: str | None = None,
                        emission_strength: float = 0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba(color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = rgba(emission)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    material.diffuse_color = rgba(color)
    return material


def seabed_material():
    material = bpy.data.materials.new("M_Seabed_Murk")
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
    noise.inputs["Scale"].default_value = 2.8
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.68
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = rgba("052c36")
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = rgba("08717b")
    bsdf.inputs["Roughness"].default_value = 0.78
    bsdf.inputs["Metallic"].default_value = 0.08
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.14
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def translucent_material(name: str, color: str, alpha: float, strength: float = 1.0,
                         glass: bool = False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    shader = nodes.new("ShaderNodeBsdfGlass" if glass else "ShaderNodeEmission")
    mix = nodes.new("ShaderNodeMixShader")
    shader.inputs["Color"].default_value = rgba(color)
    if glass:
        shader.inputs["Roughness"].default_value = 0.08
        shader.inputs["IOR"].default_value = 1.333
    else:
        shader.inputs["Strength"].default_value = strength
    mix.inputs[0].default_value = alpha
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(shader.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    if hasattr(material, "surface_render_method"):
        # Dithered transparency introduces launch-to-launch one-code-point RGB
        # noise. Blended transparency is stable and appropriate for a plate.
        material.surface_render_method = "BLENDED"
    material.diffuse_color = rgba(color, alpha)
    return material


def local_point(contract: dict, theta: float, fraction: float) -> tuple[float, float]:
    factor = contract["radial_factor"](theta) * fraction
    return (math.cos(theta) * contract["r_lng"] * factor,
            math.sin(theta) * contract["r_lat"] * factor)


def terrain_mesh(contract: dict, collection, material):
    segments = COAST_POINTS
    levels = 15
    vertices = [(0.0, 0.0, 0.24)]
    for level in range(1, levels + 1):
        t = level / levels
        for index in range(segments):
            theta = index / segments * TAU
            x, y = local_point(contract, theta, t)
            ridge = 0.055 * math.sin(theta * 5.0 + t * 7.0) * (1.0 - t)
            shelf = 0.30 * (1.0 - t ** 1.65) - 0.18 * t ** 4
            vertices.append((x, y, shelf + ridge))
    faces = []
    for index in range(segments):
        faces.append((0, 1 + index, 1 + (index + 1) % segments))
    for level in range(1, levels):
        inner = 1 + (level - 1) * segments
        outer = 1 + level * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((inner + index, outer + index, outer + nxt, inner + nxt))
    mesh = bpy.data.meshes.new("G_FMI_CoastlineTerrain")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Fish-Man Island — exact HeroRing footprint", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def flat_polygon(name: str, points: list[tuple[float, float]], z: float, collection, material):
    mesh = bpy.data.meshes.new(f"G_{name}")
    mesh.from_pydata([(x, y, z) for x, y in points], [], [tuple(range(len(points)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def curve_object(name: str, points: list[tuple[float, float, float]], collection, material,
                 bevel: float = 0.012, cyclic: bool = False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def create_caustics(contract: dict, collection, material) -> None:
    art_rng = Rng("blender:fish-man-island:caustics")
    for index in range(18):
        start = art_rng.range(0, TAU)
        sweep = art_rng.range(0.38, 0.9)
        radius = art_rng.range(0.18, 0.86)
        points = []
        for step in range(18):
            theta = start + sweep * step / 17
            t = radius + 0.018 * math.sin(step * 0.9 + index)
            x, y = local_point(contract, theta, t)
            points.append((x, y, 0.56 + 0.005 * index))
        curve_object(f"Caustic {index + 1:02d}", points, collection, material,
                     bevel=art_rng.range(0.004, 0.010))


def create_light_shafts(contract: dict, collection, materials: list) -> None:
    for index, theta in enumerate((2.10, 1.72, 1.34, 0.96)):
        center = theta + 0.18
        p0 = local_point(contract, center - 0.08, 0.76)
        p1 = local_point(contract, center + 0.08, 0.76)
        p2 = local_point(contract, center + 0.18, 0.12)
        p3 = local_point(contract, center - 0.05, 0.18)
        flat_polygon(f"Light shaft {index + 1}", [p0, p1, p2, p3],
                     0.73 + index * 0.004, collection, materials[index % len(materials)])


def create_coral(contract: dict, collection, materials: list) -> None:
    art_rng = Rng("blender:fish-man-island:coral")
    for cluster in range(44):
        theta = art_rng.range(0, TAU)
        t = art_rng.range(0.22, 0.78)
        x, y = local_point(contract, theta, t)
        branches = 2 + int(art_rng.range(0, 2.99))
        for branch in range(branches):
            angle = TAU * branch / branches + art_rng.range(-0.35, 0.35)
            spread = art_rng.range(0.015, 0.065)
            bx = x + math.cos(angle) * spread
            by = y + math.sin(angle) * spread
            height = art_rng.range(0.12, 0.42) * (1.0 - 0.25 * t)
            radius = art_rng.range(0.018, 0.045)
            bpy.ops.mesh.primitive_cone_add(
                vertices=7,
                radius1=radius,
                radius2=radius * art_rng.range(0.20, 0.58),
                depth=height,
                location=(bx, by, -0.02 + height / 2),
            )
            obj = bpy.context.object
            obj.name = f"Coral {cluster + 1:02d}.{branch + 1}"
            obj.rotation_euler[0] = art_rng.range(-0.28, 0.28)
            obj.rotation_euler[1] = art_rng.range(-0.28, 0.28)
            obj.data.materials.append(materials[(cluster + branch) % len(materials)])
            move_to_collection(obj, collection)


def create_city(contract: dict, collection, materials: list) -> None:
    art_rng = Rng("blender:fish-man-island:city")
    for index in range(13):
        theta = index / 13 * TAU + art_rng.range(-0.12, 0.12)
        t = art_rng.range(0.04, 0.30)
        x, y = local_point(contract, theta, t)
        height = art_rng.range(0.18, 0.54)
        radius = art_rng.range(0.025, 0.065)
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=radius, radius2=radius * 0.14,
                                        depth=height, location=(x, y, 0.20 + height / 2))
        obj = bpy.context.object
        obj.name = f"Ryugu glow spire {index + 1:02d}"
        obj.data.materials.append(materials[index % len(materials)])
        move_to_collection(obj, collection)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24,
                                        location=(0.0, 0.0, 0.52), scale=(0.19, 0.15, 0.16))
    center = bpy.context.object
    center.name = "Ryugu heart glow"
    center.data.materials.append(materials[0])
    move_to_collection(center, collection)


def create_dome(contract: dict, collection, glass_material, rim_material) -> None:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=96,
        ring_count=48,
        location=(0.0, 0.0, 0.34),
        scale=(contract["r_lng"] * 0.69, contract["r_lat"] * 0.69, 0.80),
    )
    dome = bpy.context.object
    dome.name = "Bubble dome"
    dome.data.materials.append(glass_material)
    move_to_collection(dome, collection)

    full_ring = []
    for index in range(129):
        theta = index / 128 * TAU
        full_ring.append((math.cos(theta) * contract["r_lng"] * 0.69,
                          math.sin(theta) * contract["r_lat"] * 0.69, 0.72))
    curve_object("Bubble dome rim", full_ring, collection, rim_material, bevel=0.015, cyclic=True)

    highlight = []
    for index in range(49):
        theta = 0.16 * math.pi + index / 48 * 0.60 * math.pi
        highlight.append((math.cos(theta) * contract["r_lng"] * 0.635,
                          math.sin(theta) * contract["r_lat"] * 0.635, 0.88))
    curve_object("Bubble dome rim highlight", highlight, collection, rim_material, bevel=0.026)


def setup_camera_and_lights(contract: dict, resolution: int):
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Top-down plate camera")
    camera = bpy.data.objects.new("Top-down plate camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 12.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.data.type = "ORTHO"

    max_extent = max(
        max(abs(x) for x, _ in contract["ring_local"]),
        max(abs(y) for _, y in contract["ring_local"]),
    )
    half_span = max_extent * 1.14
    camera.data.ortho_scale = half_span * 2.0
    scene.camera = camera

    key_data = bpy.data.lights.new("Surface light", "AREA")
    key_data.energy = 720.0
    key_data.color = (0.35, 0.78, 1.0)
    key_data.shape = "DISK"
    key_data.size = 3.2
    key = bpy.data.objects.new("Surface light", key_data)
    scene.collection.objects.link(key)
    key.location = (-2.5, 1.8, 6.2)

    warm_data = bpy.data.lights.new("Kingdom fill", "POINT")
    warm_data.energy = 260.0
    warm_data.color = (1.0, 0.28, 0.14)
    warm_data.shadow_soft_size = 1.2
    warm = bpy.data.objects.new("Kingdom fill", warm_data)
    scene.collection.objects.link(warm)
    warm.location = (0.1, -0.1, 1.6)

    world = bpy.data.worlds.new("Deep sea world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = rgba("001a26")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12
    scene.world = world

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    # Blender's output dither intentionally perturbs 8-bit RGB by one code
    # point between launches. Disable it so CI rerenders are byte-stable.
    scene.render.dither_intensity = 0.0
    scene.render.film_transparent = True
    scene.render.image_settings.compression = 25
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.color_mode = "RGBA"
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
    glare.threshold = 0.9
    glare.size = 7
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])
    return half_span


def build_scene(contract: dict, resolution: int) -> float:
    clear_scene()
    scene = bpy.context.scene
    scene["asset_track"] = "Grand Line Interface island plates"
    scene["plate_id"] = SLUG
    scene["repo_is_read_only"] = True
    scene["integration_status"] = "asset-only; no app plate loader exists yet"

    bathymetry = make_collection("01_Bathymetry")
    coral = make_collection("02_Coral")
    city = make_collection("03_Ryugu_Glow")
    dome = make_collection("04_Bubble_Dome")
    atmosphere = make_collection("05_Deep_Atmosphere")

    seabed = seabed_material()
    coast_ink = translucent_material("M_Coast_Ink", "1bc4d2", 0.80, 2.0)
    caustic = translucent_material("M_Caustics", "9befff", 0.42, 3.6)
    shaft_a = translucent_material("M_Light_Shaft_A", "79deff", 0.11, 2.4)
    shaft_b = translucent_material("M_Light_Shaft_B", "b4f4ff", 0.075, 3.0)
    fog = translucent_material("M_Volumetric_Murk_Card", "0a6171", 0.10, 0.75)
    glass = translucent_material("M_Bubble_Glass", "79e9ff", 0.18, glass=True)
    rim = translucent_material("M_Bubble_Rim", "baf8ff", 0.82, 5.0)
    coral_mats = [
        principled_material("M_Coral_Magenta", "d63c8c", roughness=0.44, emission="ff4aa2", emission_strength=0.28),
        principled_material("M_Coral_Orange", "ee6848", roughness=0.48, emission="ff855e", emission_strength=0.20),
        principled_material("M_Coral_Gold", "d7a24a", roughness=0.52, emission="ffd27a", emission_strength=0.18),
        principled_material("M_Coral_Teal", "159b94", roughness=0.46, emission="5be6dc", emission_strength=0.16),
    ]
    city_mats = [
        principled_material("M_Ryugu_Heart", "ffb45a", roughness=0.25, metallic=0.16,
                            emission="ff8738", emission_strength=4.0),
        principled_material("M_Ryugu_Pearl", "70d4dd", roughness=0.22, metallic=0.24,
                            emission="88f3ff", emission_strength=2.2),
    ]

    terrain_mesh(contract, bathymetry, seabed)
    inner_coast = [(*local_point(contract, i / COAST_POINTS * TAU, 0.985), 0.03)
                   for i in range(COAST_POINTS)]
    curve_object("Inner coastline glow", inner_coast, bathymetry, coast_ink, bevel=0.013, cyclic=True)
    create_coral(contract, coral, coral_mats)
    create_city(contract, city, city_mats)
    create_dome(contract, dome, glass, rim)
    create_caustics(contract, atmosphere, caustic)
    create_light_shafts(contract, atmosphere, [shaft_a, shaft_b])
    fog_points = [local_point(contract, i / COAST_POINTS * TAU, 0.992) for i in range(COAST_POINTS)]
    flat_polygon("Deep distance fog", fog_points, 0.67, atmosphere, fog)
    return setup_camera_and_lights(contract, resolution)


def write_contract_files(contract: dict, half_span: float, resolution: int, repo: Path,
                         png_path: Path, preview_path: Path, blend_path: Path) -> None:
    center_lng = contract["coord"]["lng"]
    center_lat = contract["coord"]["lat"]
    west, east = center_lng - half_span, center_lng + half_span
    south, north = center_lat - half_span, center_lat + half_span
    coordinates = [
        [round(west, 6), round(north, 6)],
        [round(east, 6), round(north, 6)],
        [round(east, 6), round(south, 6)],
        [round(west, 6), round(south, 6)],
    ]

    geometry = {
        "type": "FeatureCollection",
        "_meta": {
            "generator": "scripts/build_fishman_plate.py",
            "source_contract": "atlas HeroRing/radius_fn, 128 vertices",
            "coordinates_are_rounded_like_atlas": True,
        },
        "features": [{
            "type": "Feature",
            "properties": {"slug": SLUG, "debut": contract["island"]["debut_chapter"],
                           "biome": contract["biome"]},
            "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in contract["ring_geo"]] +
                                                                   [list(contract["ring_geo"][0])]]},
        }],
    }
    geometry_path = ASSET_ROOT / "geometry/fish-man-island-coastline.geojson"
    geometry_path.write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")

    try:
        repo_head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        repo_head = None
    source_hashes = {str(path.relative_to(repo)): sha256_file(path) for path in contract["inputs"]}

    manifest = {
        "schema_version": 1,
        "integration_status": "asset-only; atlas currently has no plate-loading layer",
        "repo_write_contract": "read-only",
        "plates": [{
            "id": SLUG,
            "label": "Fish-Man Island — deep pilot",
            "source_blend": "source/fish-man-island.blend",
            "raster": "renders/fish-man-island.png",
            "preview": "renders/fish-man-island-preview.png",
            "coastline": "geometry/fish-man-island-coastline.geojson",
            "projection": "MapLibre image source coordinates, equirectangular near equator",
            "coordinates": coordinates,
            "center": [center_lng, center_lat],
            "pixel_size": [resolution, resolution],
            "alpha_contract": "opaque only inside the deterministic 128-point HeroRing footprint",
            "coastline_contract": {
                "seed": f"silhouette:{SLUG}",
                "weight": contract["weight"],
                "biome": contract["biome"],
                "radius": round(contract["radius"], 12),
                "elong": round(contract["elong"], 12),
                "points": COAST_POINTS,
            },
            "spoiler_gate": {"debut_chapter": contract["island"]["debut_chapter"]},
            "descent_contract": {
                "body": [-5.9349, -2.8548],
                "dive_base": [-48.2843, 2.9],
                "chapters": {"dive": 602, "deep": 605, "riseStart": 651, "surface": 653},
                "depth_meters": 10000,
            },
            "art_direction": ["deep teal murk", "surface light shafts", "bubble rim highlight",
                              "coral distance field", "warm Ryugu glow", "caustic arcs"],
        }],
        "source": {
            "repo": str(repo),
            "git_head_at_build": repo_head,
            "input_sha256": source_hashes,
        },
        "build": {
            "blender": bpy.app.version_string,
            "script": "scripts/build_fishman_plate.py",
            "raster_sha256": sha256_file(png_path),
            "preview_sha256": sha256_file(preview_path),
            "blend_sha256": sha256_file(blend_path),
        },
    }
    manifest_path = ASSET_ROOT / "manifests/island-plates.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        other_plates = [plate for plate in existing.get("plates", []) if plate.get("id") != SLUG]
        existing.update({
            "schema_version": manifest["schema_version"],
            "integration_status": manifest["integration_status"],
            "repo_write_contract": manifest["repo_write_contract"],
            "plates": manifest["plates"] + other_plates,
            # These two legacy top-level blocks remain the Fish-Man pilot's
            # source/build record; additional plates keep per-entry builds.
            "source": manifest["source"],
            "build": manifest["build"],
        })
        manifest = existing
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = cli_args()
    repo = args.repo.resolve()
    if not (repo / "scripts/gen_silhouettes.py").exists():
        raise SystemExit(f"Atlas repo not found: {repo}")
    for directory in (ASSET_ROOT / "source", ASSET_ROOT / "renders", ASSET_ROOT / "manifests",
                      ASSET_ROOT / "geometry", ASSET_ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)

    contract = coastline_contract(repo)
    half_span = build_scene(contract, args.resolution)
    blend_path = ASSET_ROOT / "source/fish-man-island.blend"
    png_path = ASSET_ROOT / "renders/fish-man-island.png"
    preview_path = ASSET_ROOT / "renders/fish-man-island-preview.png"
    bpy.context.scene.render.filepath = str(png_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    subprocess.run(["sips", "-Z", "768", str(png_path), "--out", str(preview_path)],
                   check=True, stdout=subprocess.DEVNULL)
    write_contract_files(contract, half_span, args.resolution, repo, png_path, preview_path, blend_path)
    print(f"PLATE={png_path}")
    print(f"BLEND={blend_path}")
    print(f"MANIFEST={ASSET_ROOT / 'manifests/island-plates.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
