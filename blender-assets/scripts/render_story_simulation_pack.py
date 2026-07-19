#!/usr/bin/env python3
"""Render deterministic review boards and a short sampler for a story pack."""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1280, 720


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


TITLE_FONT = font(32, True)
SMALL_FONT = font(18, True)


def lerp(a: float, b: float, amount: float) -> float:
    return a + (b - a) * amount


def ease(amount: float, name: str | None) -> float:
    amount = max(0.0, min(1.0, amount))
    if name == "smooth":
        return amount * amount * (3 - 2 * amount)
    if name == "accelerate":
        return amount * amount
    if name == "decelerate":
        return 1 - (1 - amount) * (1 - amount)
    return amount


def actor_state(keyframes: list[dict], time_ms: float) -> dict:
    previous = keyframes[0]
    following = keyframes[-1]
    for frame in keyframes:
        if frame["t"] <= time_ms:
            previous = frame
        if frame["t"] >= time_ms:
            following = frame
            break
    span = following["t"] - previous["t"]
    amount = 0 if span <= 0 else (time_ms - previous["t"]) / span
    amount = ease(amount, following.get("ease"))
    state = {"pose": previous["pose"]}
    for key, default in (("x", 0), ("y", 0), ("scale", 1), ("rotation", 0), ("opacity", 1)):
        state[key] = lerp(previous.get(key, default), following.get(key, default), amount)
    return state


def vertical_gradient(image: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]):
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        amount = y / max(1, HEIGHT - 1)
        fill = tuple(round(lerp(top[i], bottom[i], amount)) for i in range(3)) + (255,)
        draw.line((0, y, WIDTH, y), fill=fill)


def draw_background(scene: dict) -> Image.Image:
    arena = scene["place"]["arena"]
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    if arena == "whisky-peak-night-town":
        vertical_gradient(image, (14, 18, 44), (62, 48, 66))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse((920, 48, 1080, 208), fill=(245, 228, 176, 225))
        draw.rectangle((0, 520, WIDTH, HEIGHT), fill=(91, 70, 58, 255))
        for x, h, tone in ((30, 250, (127, 73, 59)), (215, 300, (174, 119, 72)), (940, 285, (127, 73, 59)), (1110, 225, (174, 119, 72))):
            draw.rectangle((x, 520 - h, x + 160, 520), fill=tone + (255,), outline=(46, 38, 44, 255), width=5)
            draw.polygon((x - 18, 520 - h, x + 80, 455 - h, x + 178, 520 - h), fill=(57, 43, 51, 255))
        for x in range(80, WIDTH, 150):
            draw.ellipse((x, 420, x + 14, 434), fill=(246, 184, 78, 230))
    elif arena == "going-merry-deck":
        vertical_gradient(image, (78, 176, 226), (221, 241, 239))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 420, WIDTH, HEIGHT), fill=(28, 126, 164, 255))
        draw.ellipse((80, 405, 1200, 810), fill=(164, 105, 54, 255), outline=(84, 49, 25, 255), width=12)
        draw.polygon((640, 80, 650, 450, 910, 430), fill=(239, 235, 218, 235), outline=(70, 50, 30, 255))
    elif arena == "arabasta-coastal-waters":
        vertical_gradient(image, (97, 194, 229), (236, 193, 112))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 350, WIDTH, HEIGHT), fill=(23, 126, 168, 255))
        for y in range(390, HEIGHT, 52):
            draw.arc((60, y - 20, WIDTH - 60, y + 36), 190, 350, fill=(173, 225, 235, 145), width=5)
        draw.polygon(((0, 410), (190, 350), (360, 390), (520, 345), (690, 390), (860, 350), (1040, 400), (WIDTH, 355), (WIDTH, 515), (0, 515)), fill=(207, 171, 103, 150))
    elif arena == "arabasta-open-desert":
        vertical_gradient(image, (241, 158, 78), (250, 224, 170))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse((1010, 72, 1160, 222), fill=(255, 230, 139, 220))
        draw.polygon(((0, 490), (220, 420), (460, 485), (730, 400), (1010, 470), (WIDTH, 410), (WIDTH, HEIGHT), (0, HEIGHT)), fill=(218, 171, 91, 255))
        draw.polygon(((0, 560), (260, 500), (520, 555), (800, 485), (1070, 550), (WIDTH, 510), (WIDTH, HEIGHT), (0, HEIGHT)), fill=(194, 142, 72, 180))
    elif arena == "alubarna-palace-rooftop":
        vertical_gradient(image, (235, 174, 91), (250, 222, 165))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 470, WIDTH, HEIGHT), fill=(210, 176, 118, 255))
        draw.rectangle((0, 475, WIDTH, 505), fill=(135, 91, 59, 255))
        for x in range(40, WIDTH, 175):
            draw.rectangle((x, 390, x + 112, 505), fill=(231, 204, 151, 255), outline=(124, 83, 55, 255), width=5)
            draw.polygon(((x - 12, 390), (x + 56, 340), (x + 124, 390)), fill=(163, 83, 45, 255))
    elif arena == "arabasta-royal-tomb":
        vertical_gradient(image, (31, 27, 35), (91, 65, 48))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 505, WIDTH, HEIGHT), fill=(74, 57, 50, 255))
        for x in (70, 270, 950, 1150):
            draw.rectangle((x, 130, x + 90, 540), fill=(105, 83, 64, 255), outline=(173, 135, 84, 210), width=5)
        draw.polygon(((370, 505), (455, 250), (825, 250), (910, 505)), fill=(55, 44, 43, 255), outline=(162, 124, 81, 220))
        draw.ellipse((560, 300, 720, 460), fill=(228, 177, 78, 75))
    elif arena == "skypiea-golden-bell":
        vertical_gradient(image, (91, 184, 238), (239, 248, 245))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 500, WIDTH, HEIGHT), fill=(221, 236, 233, 255))
        for x, y, rx, ry in ((40, 360, 270, 115), (330, 430, 360, 105), (850, 355, 390, 130)):
            draw.ellipse((x, y, x + rx, y + ry), fill=(252, 255, 255, 215))
        draw.rectangle((598, 150, 682, 535), fill=(94, 126, 74, 255), outline=(55, 88, 51, 255), width=6)
        draw.polygon(((525, 236), (640, 88), (755, 236)), fill=(223, 174, 54, 255), outline=(255, 226, 128, 255))
        draw.ellipse((548, 198, 732, 430), outline=(251, 212, 91, 230), width=18)
    elif arena == "enies-lobby-undersea-tunnel":
        vertical_gradient(image, (18, 45, 65), (54, 86, 99))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 500, WIDTH, HEIGHT), fill=(62, 71, 75, 255))
        for x in (70, 260, 930, 1120):
            draw.rectangle((x, 100, x + 95, 540), fill=(86, 96, 98, 255), outline=(143, 158, 156, 180), width=5)
        draw.arc((250, 45, 1030, 740), 180, 360, fill=(129, 151, 151, 180), width=18)
        for y in range(145, 500, 85):
            draw.line((170, y, 1110, y), fill=(94, 121, 128, 80), width=3)
    else:
        vertical_gradient(image, (244, 173, 89), (238, 218, 172))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((0, 515, WIDTH, HEIGHT), fill=(204, 166, 105, 255))
        for x, h in ((50, 235), (250, 285), (955, 260), (1120, 215)):
            draw.rectangle((x, 515 - h, x + 145, 515), fill=(220, 189, 126, 255), outline=(116, 80, 50, 255), width=5)
            draw.polygon((x - 12, 515 - h, x + 72, 455 - h, x + 157, 515 - h), fill=(150, 78, 44, 255))
    return image


def draw_events(image: Image.Image, scene: dict, time_ms: float):
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(sum(ord(char) for char in scene["id"]))
    for event in scene["events"]:
        duration = event.get("duration_ms", 700)
        progress = (time_ms - event["t"]) / duration
        if not 0 <= progress <= 1:
            continue
        intensity = event.get("intensity", 1.0)
        alpha = round(255 * (1 - progress) * intensity)
        kind = event["type"]
        if kind in {"slash", "fire-wall", "fire-fist-wave", "sand-blade", "kick-trail", "ballet-spin", "spike-thrust", "tornado", "golden-rifle", "tempest-kick"}:
            color = (235, 246, 255, alpha) if kind in {"slash", "kick-trail"} else (255, 134, 38, alpha)
            if kind == "sand-blade":
                color = (224, 179, 93, alpha)
            elif kind == "ballet-spin":
                color = (255, 165, 220, alpha)
            elif kind == "spike-thrust":
                color = (218, 226, 235, alpha)
            elif kind == "tornado":
                color = (210, 238, 252, alpha)
            elif kind == "golden-rifle":
                color = (255, 217, 76, alpha)
            elif kind == "tempest-kick":
                color = (215, 244, 255, alpha)
            if kind == "fire-fist-wave":
                width = 160 + round(progress * 520)
                x0 = round(250 + progress * 300)
                draw.rounded_rectangle((x0, 320, min(WIDTH - 80, x0 + width), 430), radius=52, fill=(255, 116, 25, min(alpha, 185)), outline=(255, 226, 90, alpha), width=14)
            else:
                draw.arc((330, 170, 950, 650), 205, 338, fill=color, width=round(18 * intensity))
        elif kind in {"impact", "route-pulse", "smoke-fire-clash", "hana-hana-bloom", "clone-flash", "steel-sparks", "weather-heat", "weather-cool", "wet-sand-impact", "dehydration-pulse", "poison-flash", "blood-counter-impact", "victory-pulse", "rubber-immunity-pulse", "gold-ball-weight", "golden-bell-impact", "gear-third-impact", "rokuogan-shockwave", "defeat-impact"}:
            color = (255, 236, 174, alpha)
            if kind == "hana-hana-bloom":
                color = (205, 126, 213, alpha)
            elif kind == "smoke-fire-clash":
                color = (255, 175, 95, alpha)
            elif kind == "clone-flash":
                color = (255, 174, 224, alpha)
            elif kind == "steel-sparks":
                color = (220, 240, 255, alpha)
            elif kind == "weather-heat":
                color = (255, 157, 54, alpha)
            elif kind in {"weather-cool", "wet-sand-impact"}:
                color = (125, 211, 255, alpha)
            elif kind == "dehydration-pulse":
                color = (204, 168, 104, alpha)
            elif kind == "poison-flash":
                color = (188, 96, 236, alpha)
            elif kind == "blood-counter-impact":
                color = (176, 92, 70, alpha)
            elif kind == "victory-pulse":
                color = (255, 221, 112, alpha)
            elif kind == "rubber-immunity-pulse":
                color = (255, 244, 125, alpha)
            elif kind in {"gold-ball-weight", "golden-bell-impact"}:
                color = (255, 211, 68, alpha)
            elif kind == "gear-third-impact":
                color = (244, 208, 167, alpha)
            elif kind == "rokuogan-shockwave":
                color = (226, 246, 255, alpha)
            elif kind == "defeat-impact":
                color = (255, 235, 205, alpha)
            radius = 35 + progress * 230
            draw.ellipse((WIDTH / 2 - radius, HEIGHT * 0.53 - radius, WIDTH / 2 + radius, HEIGHT * 0.53 + radius), outline=color, width=10)
        elif kind in {"smoke", "dust", "crowd", "sand-body-disperse", "sandstorm", "moisture-drain", "thunder-field", "gear-second-steam"}:
            color = (224, 226, 224, min(alpha, 100)) if kind == "smoke" else (190, 165, 120, min(alpha, 90))
            if kind in {"sand-body-disperse", "sandstorm"}:
                color = (220, 174, 90, min(alpha, 125))
            elif kind == "moisture-drain":
                color = (220, 199, 151, min(alpha, 120))
            elif kind == "thunder-field":
                color = (103, 210, 255, min(alpha, 145))
            elif kind == "gear-second-steam":
                color = (255, 216, 231, min(alpha, 115))
            for _ in range(28):
                x = rng.randint(250, 1030)
                y = rng.randint(350, 650)
                radius = rng.randint(12, 42)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        elif kind == "quicksand":
            radius_x = 120 + progress * 210
            radius_y = 35 + progress * 58
            center = (WIDTH * 0.47, HEIGHT * 0.79)
            for ring in range(4):
                inset = ring * 22
                draw.ellipse((center[0] - radius_x + inset, center[1] - radius_y + inset / 4, center[0] + radius_x - inset, center[1] + radius_y - inset / 4), outline=(184, 133, 65, max(25, alpha - ring * 35)), width=7)
        elif kind in {"water-splash", "water-spray", "water-drop"}:
            center = (WIDTH * 0.5, HEIGHT * 0.53)
            if kind == "water-drop":
                y = 120 + progress * 360
                draw.ellipse((center[0] - 18, y - 34, center[0] + 18, y + 34), fill=(136, 218, 255, alpha))
            else:
                width = 90 + progress * (360 if kind == "water-spray" else 180)
                draw.rounded_rectangle((center[0] - width / 2, center[1] - 28, center[0] + width / 2, center[1] + 28), radius=25, fill=(114, 204, 244, min(alpha, 170)))
        elif kind == "gum-gum-storm":
            for index in range(12):
                x = 420 + (index % 4) * 105 + rng.randint(-16, 16)
                y = 600 - progress * 360 - (index // 4) * 80
                draw.line((x, y + 130, x + rng.randint(-24, 24), y), fill=(244, 218, 172, min(alpha, 180)), width=16)
        elif kind == "jet-gatling":
            for index in range(18):
                row = index // 6
                y = 250 + row * 92 + rng.randint(-16, 16)
                x0 = 315 + rng.randint(-20, 25)
                x1 = 735 + progress * 170 + rng.randint(-35, 40)
                draw.line((x0, y, x1, y + rng.randint(-18, 18)), fill=(247, 215, 175, min(alpha, 205)), width=13)
                draw.ellipse((x1 - 24, y - 22, x1 + 24, y + 22), fill=(245, 207, 164, min(alpha, 200)))
        elif kind in {"speed-lines", "wind", "jet-strike"}:
            for index in range(22):
                y = 120 + index * 22 + rng.randint(-5, 5)
                x = (round(progress * (WIDTH + 420)) + index * 83) % (WIDTH + 420) - 210
                draw.line((x, y, x + 180 * intensity, y - 18), fill=(232, 246, 250, 105), width=4)
        elif kind in {"enel-lightning", "finger-pistol-flash"}:
            color = (86, 205, 255, alpha) if kind == "enel-lightning" else (245, 250, 255, alpha)
            x = WIDTH * (0.58 if kind == "enel-lightning" else 0.52)
            draw.line((x, 100, x - 80, 310, x + 35, 290, x - 40, 560), fill=color, width=18)
        elif kind in {"fire-burst", "explosion"}:
            center = (WIDTH * 0.48, HEIGHT * 0.54)
            radius = 45 + progress * 190
            draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(255, 125, 32, min(alpha, 150)))


def make_pose_loader(pose_root: Path):
    @lru_cache(maxsize=128)
    def load_pose(asset_id: str, pose: str) -> Image.Image:
        path = pose_root / asset_id / "poses" / f"{pose}.png"
        if not path.exists():
            raise FileNotFoundError(path)
        return Image.open(path).convert("RGBA")

    return load_pose


def draw_actor(image: Image.Image, actor: dict, state: dict, map_height: float, load_pose):
    pose = load_pose(actor["asset_id"], state["pose"])
    side = max(20, round(430 * state["scale"] * map_height))
    pose = pose.resize((side, side), Image.Resampling.LANCZOS)
    if state["opacity"] < 0.999:
        pose.putalpha(pose.getchannel("A").point(lambda value: round(value * state["opacity"])))
    if abs(state["rotation"]) > 0.01:
        pose = pose.rotate(-state["rotation"], Image.Resampling.BICUBIC, expand=True)
    x = WIDTH * (0.5 + state["x"] * 0.42)
    ground = HEIGHT * 0.86 - state["y"] * HEIGHT * 0.5
    image.alpha_composite(pose, (round(x - pose.width / 2), round(ground - pose.height)))


def render_scene(scene: dict, time_ms: float, character_meta: dict, load_pose) -> Image.Image:
    image = draw_background(scene)
    draw_events(image, scene, time_ms)
    for actor in sorted(scene["actors"], key=lambda item: item.get("z", 0)):
        draw_actor(image, actor, actor_state(actor["keyframes"], time_ms), character_meta[actor["asset_id"]]["map_height"], load_pose)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((28, 24, WIDTH - 28, 108), radius=18, fill=(8, 13, 19, 188), outline=(236, 209, 128, 170), width=2)
    draw.text((52, 38), scene["label"], font=TITLE_FONT, fill=(255, 249, 225, 255))
    gate = scene["chapter_gate"]
    draw.text((52, 80), f"Chapters {gate['start']}–{gate['end']} · {scene['type']} · RUNTIME READY", font=SMALL_FONT, fill=(168, 216, 232, 255))
    progress = max(0, min(1, time_ms / scene["duration_ms"]))
    draw.rounded_rectangle((40, HEIGHT - 28, WIDTH - 40, HEIGHT - 16), radius=6, fill=(8, 12, 18, 170))
    draw.rounded_rectangle((40, HEIGHT - 28, 40 + (WIDTH - 80) * progress, HEIGHT - 16), radius=6, fill=(236, 187, 80, 230))
    return image.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--seconds-per-scene", type=float, default=2.0)
    parser.add_argument("--fps", type=int, default=12)
    args = parser.parse_args()

    config_path = ROOT / args.config
    contract = json.loads((ROOT / args.contract).read_text())
    config = json.loads(config_path.read_text())
    pack_id = contract["id"]
    index_path = ROOT / "runtime/story-simulations" / pack_id / "character-index.json"
    index = json.loads(index_path.read_text())
    character_meta = {entry["id"]: entry for entry in index["characters"]}
    load_pose = make_pose_loader(config_path.parent / "characters")
    output = ROOT / "renders/story-simulations" / pack_id
    output.mkdir(parents=True, exist_ok=True)

    card_w, card_h = 420, 310
    catalog_rows = max(1, math.ceil(len(index["characters"]) / 3))
    catalog = Image.new("RGB", (card_w * 3, card_h * catalog_rows), (12, 18, 25))
    catalog_draw = ImageDraw.Draw(catalog)
    for position, entry in enumerate(index["characters"]):
        x = (position % 3) * card_w
        y = (position // 3) * card_h
        atlas = Image.open(ROOT / entry["atlas"]).convert("RGBA")
        atlas.thumbnail((card_w - 24, card_h - 60), Image.Resampling.LANCZOS)
        tile = Image.new("RGBA", (card_w - 20, card_h - 20), (28, 35, 45, 255))
        tile.alpha_composite(atlas, ((tile.width - atlas.width) // 2, 42))
        catalog.paste(tile.convert("RGB"), (x + 10, y + 10))
        catalog_draw.text((x + 22, y + 18), entry["id"], font=SMALL_FONT, fill=(249, 232, 184))
    catalog_path = output / "character-atlas-catalog.png"
    catalog.save(catalog_path, optimize=True)

    board = Image.new("RGB", (640 * len(contract["scenes"]), 360), (7, 11, 16))
    for position, scene in enumerate(contract["scenes"]):
        frame = render_scene(scene, scene["duration_ms"] * 0.58, character_meta, load_pose)
        frame.thumbnail((640, 360), Image.Resampling.LANCZOS)
        board.paste(frame, (position * 640, 0))
    board_path = output / "scene-board.png"
    board.save(board_path, optimize=True)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for the sampler")
    frames_per_scene = max(1, round(args.seconds_per_scene * args.fps))
    with tempfile.TemporaryDirectory(prefix=f"{pack_id}-") as directory:
        frame_dir = Path(directory)
        frame_number = 0
        poster = None
        for scene in contract["scenes"]:
            for local_frame in range(frames_per_scene):
                progress = local_frame / max(1, frames_per_scene - 1)
                image = render_scene(scene, progress * scene["duration_ms"], character_meta, load_pose)
                if poster is None:
                    poster = image.copy()
                image.save(frame_dir / f"frame-{frame_number:05d}.png")
                frame_number += 1
        assert poster is not None
        poster_path = output / "sampler-poster.png"
        poster.save(poster_path, optimize=True)
        video_path = output / "sampler.mp4"
        subprocess.run(
            [
                ffmpeg, "-y", "-framerate", str(args.fps), "-i", str(frame_dir / "frame-%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    print(f"Rendered {pack_id}: {len(contract['scenes'])} scenes")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
