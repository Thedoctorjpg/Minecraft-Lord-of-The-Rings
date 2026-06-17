"""
Download Rohan armour base textures and apply LOTRO-inspired grading for Legacy 1.7.10.

Usage:
    pip install Pillow requests
    python upgrade_rohan_armor.py
    python upgrade_rohan_armor.py --marshal-only
    python upgrade_rohan_armor.py --no-download   # use source_textures/rohan/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow required: python -m pip install Pillow") from exc

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name("rohan_armor_manifest.json")
OUTPUT_DIR = ROOT / "assets" / "lotr" / "textures" / "items"
SOURCE_DIR = ROOT / "source_textures" / "rohan"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def download_bases(manifest: dict, targets: list[str]) -> None:
    import urllib.request

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = manifest["base_url"].rstrip("/")
    for name in targets:
        url = f"{base_url}/{name}"
        dest = SOURCE_DIR / name
        if dest.exists():
            print(f"  skip (exists): {name}")
            continue
        print(f"  fetch: {name}")
        urllib.request.urlretrieve(url, dest)


def warm_metal_pixels(img: Image.Image, style: dict, marshal: bool) -> Image.Image:
    """LOTRO Rohan: warm gold plate, deeper leather gaps, marshal green trim."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a < 16:
                continue

            lum = (r + g + b) / 3.0
            if lum < 55:
                # leather / shadow — warm brown, not grey
                r = min(255, int(r * style["leather_warmth"] + 8))
                g = min(255, int(g * (style["leather_warmth"] - 0.04) + 4))
                b = max(0, int(b * (style["leather_warmth"] - 0.12)))
            elif lum > 150:
                # plate highlights — golden LOTRO sheen
                r = min(255, int(r * style["metal_warmth"]))
                g = min(255, int(g * (style["metal_warmth"] - 0.02) + 6))
                b = max(0, int(b * (style["metal_warmth"] - 0.18)))
            else:
                r = min(255, int(r * style["metal_warmth"]))
                g = min(255, int(g * (style["metal_warmth"] - 0.05)))
                b = max(0, int(b * (style["metal_warmth"] - 0.1)))

            if marshal and lum > 90 and g > r * 0.85:
                tint = style["marshal_green_tint"]
                r = min(255, int(r * tint[0]))
                g = min(255, int(g * tint[1]))
                b = min(255, int(b * tint[2]))

            pixels[x, y] = (r, g, b, a)

    return rgba


def add_plate_engraving_glow(img: Image.Image, style: dict) -> Image.Image:
    """Subtle embossed edge emphasis on bright plate regions."""
    edges = img.convert("RGBA").filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Contrast(edges).enhance(2.0)
    overlay = Image.new("RGBA", img.size, style["plate_highlight"])
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow.paste(overlay, (0, 0), edges)
    return Image.alpha_composite(img.convert("RGBA"), glow)


def upgrade_texture(path: Path, style: dict, marshal: bool) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img = warm_metal_pixels(img, style, marshal)
    img = ImageEnhance.Contrast(img).enhance(style["contrast"])
    for _ in range(style["sharpness_passes"]):
        img = img.filter(ImageFilter.SHARPEN)
    img = add_plate_engraving_glow(img, style)
    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="LOTRO-style Rohan armour upgrade for Legacy 1.7.10")
    parser.add_argument("--marshal-only", action="store_true", help="Only upgrade Marshal tier pieces")
    parser.add_argument("--no-download", action="store_true", help="Use existing source_textures/rohan/")
    parser.add_argument("--include-weapons", action="store_true", help="Also upgrade swordRohan + spearRohan")
    args = parser.parse_args()

    manifest = load_manifest()
    style = manifest["lotro_style"]
    targets = list(manifest["armor"])
    if args.include_weapons:
        targets.extend(manifest["weapons"])
    if args.marshal_only:
        targets = [t for t in targets if "Marshal" in t]

    if not args.no_download:
        print("Downloading base textures...")
        download_bases(manifest, targets)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    upgraded = 0
    for name in targets:
        src = SOURCE_DIR / name
        if not src.exists():
            print(f"  missing: {src}")
            continue
        marshal = "Marshal" in name
        out = upgrade_texture(src, style, marshal)
        dest = OUTPUT_DIR / name
        out.save(dest)
        print(f"  upgraded: {name} -> {dest.relative_to(ROOT)}")
        upgraded += 1

    print(f"\nDone — {upgraded} Rohan texture(s) in {OUTPUT_DIR}")
    print("Enable pack in 1.7.10 Forge above vanilla, test with Rohirric armour equipped.")


if __name__ == "__main__":
    main()