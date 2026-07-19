#!/usr/bin/env python3
"""Build normalized actor cells, atlases, and metadata for any story pack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def alpha_bbox(image: Image.Image, threshold: int = 12):
    alpha = image.getchannel("A")
    return alpha.point(lambda value: 255 if value >= threshold else 0).getbbox()


def subject_scale(
    sources: list[Image.Image],
    cell_size: int,
    padding: int = 16,
) -> float:
    """Return one scale for an actor's whole pose family.

    Scaling every pose independently makes a crouch, a wide sword strike, and a
    standing guard all fill the cell. At runtime that reads as the actor growing
    and shrinking on every atlas step. One scale preserves the proportions that
    were authored across the keyed sheet while the common baseline keeps the
    feet planted.
    """
    bounds = [bbox for source in sources if (bbox := alpha_bbox(source))]
    if not bounds:
        return 1.0
    max_width = max(bbox[2] - bbox[0] for bbox in bounds)
    max_height = max(bbox[3] - bbox[1] for bbox in bounds)
    available = cell_size - padding * 2
    return min(available / max_width, available / max_height)


def normalize_cell(
    source: Image.Image,
    cell_size: int,
    scale: float,
    padding: int = 16,
) -> tuple[Image.Image, dict[str, int] | None]:
    bbox = alpha_bbox(source)
    target = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    if not bbox:
        return target, None
    subject = source.crop(bbox)
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    subject = subject.resize(size, Image.Resampling.LANCZOS)
    x = (cell_size - subject.width) // 2
    y = cell_size - padding - subject.height
    target.alpha_composite(subject, (x, y))
    return target, {"x": x, "y": y, "width": subject.width, "height": subject.height}


def build_character(
    entry: dict,
    pack_id: str,
    pose_root: Path,
    runtime_root: Path,
    columns: int,
    rows: int,
    cell_size: int,
) -> dict:
    source_path = ROOT / entry["keyed_sheet"]
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    source = Image.open(source_path).convert("RGBA")
    if source.width % columns or source.height % rows:
        raise ValueError(f"{source_path} is not divisible by {columns}x{rows}")
    if len(entry["poses"]) != columns * rows:
        raise ValueError(f"{entry['id']} must define {columns * rows} poses")

    source_cell_w = source.width // columns
    source_cell_h = source.height // rows
    atlas = Image.new("RGBA", (columns * cell_size, rows * cell_size), (0, 0, 0, 0))
    pose_dir = pose_root / entry["id"] / "poses"
    runtime_dir = runtime_root / entry["id"]
    pose_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    crops = []
    for index in range(len(entry["poses"])):
        column = index % columns
        row = index // columns
        crops.append(
            source.crop(
                (
                    column * source_cell_w,
                    row * source_cell_h,
                    (column + 1) * source_cell_w,
                    (row + 1) * source_cell_h,
                )
            )
        )
    shared_scale = subject_scale(crops, cell_size)
    baseline_y = (cell_size - 16) / cell_size

    frames = {}
    for index, pose in enumerate(entry["poses"]):
        column = index % columns
        row = index // columns
        normalized, content_rect = normalize_cell(crops[index], cell_size, shared_scale)
        pose_path = pose_dir / f"{pose}.png"
        normalized.save(pose_path, optimize=True)
        x, y = column * cell_size, row * cell_size
        atlas.alpha_composite(normalized, (x, y))
        frames[pose] = {
            "index": index,
            "pixel_rect": {"x": x, "y": y, "width": cell_size, "height": cell_size},
            "uv_top_left": {
                "x": x / atlas.width,
                "y": y / atlas.height,
                "width": cell_size / atlas.width,
                "height": cell_size / atlas.height,
            },
            "pivot": {"x": 0.5, "y": baseline_y},
            "content_rect": content_rect,
        }

    atlas_path = runtime_dir / "atlas.png"
    atlas.save(atlas_path, optimize=True)
    metadata = {
        "schema_version": 1,
        "pack_id": pack_id,
        "id": entry["id"],
        "display_name": entry["display_name"],
        "kind": entry["kind"],
        "variant": entry["variant"],
        "representation": "camera-facing-2d-atlas",
        "source_sheet": entry["keyed_sheet"],
        "source_sha256": sha256(source_path),
        "atlas": str(atlas_path.relative_to(ROOT)),
        "atlas_sha256": sha256(atlas_path),
        "atlas_size": {"width": atlas.width, "height": atlas.height},
        "grid": {"columns": columns, "rows": rows, "cell_px": cell_size},
        "map_height": entry["map_height"],
        "facing": "camera",
        "normalization": {
            "mode": "shared_actor_scale",
            "subject_scale": round(shared_scale, 8),
            "baseline_y": baseline_y,
            "padding_px": 16,
        },
        "frames": frames,
        "runtime_rules": {
            "pose_interpolation": "step",
            "transform_interpolation": "linear-or-authored-ease",
            "depth_write": False,
            "alpha_test": 0.05,
            "reduced_motion": entry["poses"][-1],
        },
    }
    metadata_path = runtime_dir / "character.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return {
        "id": entry["id"],
        "kind": entry["kind"],
        "variant": entry["variant"],
        "metadata": str(metadata_path.relative_to(ROOT)),
        "atlas": str(atlas_path.relative_to(ROOT)),
        "atlas_sha256": metadata["atlas_sha256"],
        "poses": entry["poses"],
        "map_height": entry["map_height"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Character-sheet registry relative to the asset root")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text())
    pack_id = config["pack_id"]
    art_root = config_path.parent
    pose_root = art_root / "characters"
    runtime_pack = ROOT / "runtime/story-simulations" / pack_id
    runtime_root = runtime_pack / "characters"
    grid = config["grid"]
    index = [
        build_character(
            entry,
            pack_id,
            pose_root,
            runtime_root,
            grid["columns"],
            grid["rows"],
            grid["runtime_cell_px"],
        )
        for entry in config["characters"]
    ]
    output = runtime_pack / "character-index.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pack_id": pack_id,
                "representation": "camera-facing-2d-atlas",
                "character_count": len(index),
                "characters": index,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Built {len(index)} actor atlas packages for {pack_id}")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
