#!/usr/bin/env python3
"""Build a review contact sheet from the transparent Totto Land renders."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "totto-land-food-geography"
RUNTIME_RENDERS = ROOT / "renders" / "runtime"
OUTPUT = ROOT / "renders" / f"{ASSET_ID}-contact-sheet.png"


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def panel(source: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (6, 16, 27, 255))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    return canvas


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (1800, 1220), (4, 11, 20, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 45), "TOTTO LAND — FOOD-ISLAND GEOGRAPHY", fill=(255, 243, 221), font=font(46, bold=True))
    draw.text(
        (72, 105),
        "Additive hero geography • chapter gates 651 / 827 / 828 / 829 / 831 • chapter-829 open-sea event inset only",
        fill=(139, 197, 214),
        font=font(22),
    )

    master = panel(RUNTIME_RENDERS / f"{ASSET_ID}.png", (1040, 700))
    canvas.alpha_composite(master, (40, 170))
    draw.rectangle((40, 170, 1080, 870), outline=(64, 151, 178), width=3)
    draw.text((66, 190), "SYSTEM VIEW", fill=(255, 230, 169), font=font(24, bold=True))

    closeups = (
        ("WHOLE CAKE + CHATEAU / SWEET CITY / FOREST", "whole-cake"),
        ("CACAO — ENTIRELY CHOCOLATE + EDIBLE SETTLEMENT", "cacao"),
        ("BISCUITS — VERIFIED NAME, INTERPOLATED THEME FORM", "biscuits"),
    )
    for index, (label, suffix) in enumerate(closeups):
        y = 170 + index * 235
        image = panel(RUNTIME_RENDERS / f"{ASSET_ID}-{suffix}.png", (650, 205))
        canvas.alpha_composite(image, (1110, y))
        draw.rectangle((1110, y, 1760, y + 205), outline=(104, 86, 134), width=3)
        draw.text((1128, y + 14), label, fill=(255, 242, 224), font=font(17, bold=True))

    draw.rounded_rectangle((40, 915, 1760, 1170), radius=18, fill=(8, 24, 37), outline=(66, 110, 129), width=3)
    draw.text((70, 945), "EVIDENCE BOUNDARY", fill=(245, 196, 105), font=font(23, bold=True))
    notes = (
        "• Cacao Island is named and described by the local chapter-827 feed as entirely chocolate.",
        "• Biscuits Island is a verified manga island at chapter 828; exact terrain remains visual interpolation.",
        "• Sweet City and the Forest of Temptation are locally named in chapters 829 and 831.",
        "• 'Chocolate Town' is not a structured local label; the asset uses cacao-chocolate-settlement.",
        "• No local evidence established a juice river, chocolate river, or inland canal, so none was modeled.",
    )
    for index, note in enumerate(notes):
        draw.text((74, 992 + index * 31), note, fill=(203, 222, 227), font=font(18))

    canvas.convert("RGB").save(OUTPUT, quality=95)
    print(f"CONTACT_SHEET={OUTPUT}")


if __name__ == "__main__":
    main()
