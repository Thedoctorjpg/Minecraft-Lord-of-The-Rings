"""
LOTRO moon-glow upgrade for ithildin + elvish runes (Legacy 1.7.10).

Modes:
  material       — ithildin ingot, pale starlight silver
  rune_block     — carved high-elven stonework, luminous rune lines
  glowing_weapon — elven blades with script glow
  ithildin_block — derived Moria-style ithildin block (dark stone + bright runes)

Usage:
    python upgrade_ithildin_runes.py
    python upgrade_ithildin_runes.py --blocks-only
    python upgrade_ithildin_runes.py --weapons-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name("ithildin_manifest.json")
SOURCE = ROOT / "source_textures" / "ithildin"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def fetch_asset(manifest: dict, rel: str, dest: Path) -> bool:
    url = f"{manifest['base_repo']}/assets/lotr/{rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return True
    print(f"  fetch: {rel}")
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except urllib.error.HTTPError:
        return False


def download_targets(manifest: dict, rels: list[str]) -> None:
    print("Downloading base ithildin / rune textures...")
    for rel in rels:
        fetch_asset(manifest, rel, SOURCE / rel)
        fetch_asset(manifest, f"{rel}.mcmeta", SOURCE / f"{rel}.mcmeta")


def is_rune_pixel(r: int, g: int, b: int, lum: float, style: dict) -> bool:
    if lum >= style["rune_bright_threshold"]:
        return True
    if lum >= style["rune_lum_threshold"] and b >= r * 0.85 and g >= r * 0.8:
        return True
    return False


def moon_rune_color(
    r: int, g: int, b: int, a: int, style: dict, *, intense: bool = False
) -> tuple[int, int, int]:
    if a < 16:
        return r, g, b

    lum = (r + g + b) / 3.0
    factor = style["stone_cool_factor"] - (0.12 if intense else 0.0)

    if is_rune_pixel(r, g, b, lum, style):
        boost = 1.35 if intense else 1.2
        r = min(255, int(r * 0.55 * boost + 175))
        g = min(255, int(g * 0.75 * boost + 205))
        b = min(255, int(b * 0.95 * boost + 235))
    elif lum > 75:
        r = min(255, int(r * 0.82 + 12))
        g = min(255, int(g * 0.9 + 18))
        b = min(255, int(b * 1.05 + 28))
    else:
        r = max(0, int(r * factor))
        g = max(0, int(g * (factor + 0.04)))
        b = min(255, int(b * (factor + 0.18) + 10))

    return r, g, b


def ithildin_material_color(r: int, g: int, b: int, a: int) -> tuple[int, int, int]:
    if a < 16:
        return r, g, b
    lum = (r + g + b) / 3.0
    if lum > 140:
        r = min(255, int(r * 0.75 + 200))
        g = min(255, int(g * 0.88 + 220))
        b = min(255, int(b * 1.0 + 245))
    elif lum > 60:
        r = min(255, int(r * 0.8 + 40))
        g = min(255, int(g * 0.92 + 70))
        b = min(255, int(b * 1.1 + 110))
    else:
        r = max(0, int(r * 0.55 + 15))
        g = max(0, int(g * 0.65 + 25))
        b = min(255, int(b * 0.95 + 55))
    return r, g, b


def glowing_weapon_color(r: int, g: int, b: int, a: int, style: dict) -> tuple[int, int, int]:
    if a < 16:
        return r, g, b
    lum = (r + g + b) / 3.0

    if is_rune_pixel(r, g, b, lum, style) or (b > 150 and lum > 40):
        return moon_rune_color(r, g, b, a, style, intense=True)
    if lum > 90:
        r = min(255, int(r * 0.9 + 8))
        g = min(255, int(g * 0.95 + 12))
        b = min(255, int(b * 1.08 + 18))
    else:
        r = max(0, int(r * 0.78))
        g = max(0, int(g * 0.82))
        b = min(255, int(b * 0.95 + 6))
    return r, g, b


def apply_glow_overlay(img: Image.Image, glow_color: list[int], threshold: int) -> Image.Image:
    rgba = img.convert("RGBA")
    glow = Image.new("RGBA", rgba.size, tuple(glow_color))
    mask = rgba.convert("L").point(lambda p: 255 if p > threshold else 0)
    layer = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    layer.paste(glow, (0, 0), mask)
    return Image.alpha_composite(rgba, layer)


def process_pixels(img: Image.Image, mode: str, style: dict) -> Image.Image:
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if mode == "material":
                nr, ng, nb = ithildin_material_color(r, g, b, a)
            elif mode == "glowing_weapon":
                nr, ng, nb = glowing_weapon_color(r, g, b, a, style)
            else:
                intense = mode == "ithildin_block"
                nr, ng, nb = moon_rune_color(r, g, b, a, style, intense=intense)
            pixels[x, y] = (nr, ng, nb, a)

    rgba = ImageEnhance.Contrast(rgba).enhance(style["contrast"])
    rgba = rgba.filter(ImageFilter.SHARPEN)

    glow = style["ithildin_glow_color"] if mode == "material" else style["moon_glow_color"]
    threshold = 90 if mode in {"rune_block", "ithildin_block"} else 105
    return apply_glow_overlay(rgba, glow, threshold)


def upgrade_file(src: Path, dest: Path, mode: str, style: dict) -> None:
    result = process_pixels(Image.open(src), mode, style)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result.save(dest)
    mcmeta = src.with_suffix(src.suffix + ".mcmeta")
    if mcmeta.exists():
        shutil.copy2(mcmeta, dest.with_suffix(dest.suffix + ".mcmeta"))


def output_path(rel: str) -> Path:
    if rel.startswith("textures/items/"):
        return ROOT / "assets" / "lotr" / "textures" / "items" / Path(rel).name
    if rel.startswith("textures/blocks/"):
        return ROOT / "assets" / "lotr" / "textures" / "blocks" / Path(rel).name
    raise ValueError(rel)


def mode_for_rel(rel: str, manifest: dict) -> str:
    if rel in manifest["ithildin_material"]:
        return "material"
    if rel in manifest["glowing_weapons"]:
        return "glowing_weapon"
    return "rune_block"


def collect_downloads(manifest: dict) -> list[str]:
    rels = (
        manifest["ithildin_material"]
        + manifest["rune_blocks"]
        + manifest["glowing_weapons"]
    )
    for derived in manifest.get("derived_blocks", []):
        rels.append(derived["source"])
    return list(dict.fromkeys(rels))


def main() -> None:
    parser = argparse.ArgumentParser(description="LOTRO ithildin + elvish rune upgrade")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--blocks-only", action="store_true")
    parser.add_argument("--weapons-only", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    style = manifest["lotro_style"]

    if not args.no_download:
        download_targets(manifest, collect_downloads(manifest))

    jobs: list[tuple[str, str, str]] = []

    if not args.weapons_only:
        for rel in manifest["ithildin_material"] + manifest["rune_blocks"]:
            jobs.append((rel, rel, mode_for_rel(rel, manifest)))
        for derived in manifest.get("derived_blocks", []):
            jobs.append((derived["source"], derived["output"], derived["mode"]))

    if not args.blocks_only:
        for rel in manifest["glowing_weapons"]:
            jobs.append((rel, rel, "glowing_weapon"))

    upgraded = 0
    print("Upgrading ithildin / elvish rune textures...")
    for src_rel, out_rel, mode in jobs:
        src = SOURCE / src_rel
        if not src.exists():
            print(f"  missing: {src_rel}")
            continue
        dest = output_path(out_rel)
        upgrade_file(src, dest, mode, style)
        print(f"  [{mode}] {out_rel}")
        upgraded += 1

    print(f"\nDone — {upgraded} texture(s) ready.")
    print("Place Moria doors / ithildin blocks near moonlight in-game to check rune glow.")


if __name__ == "__main__":
    main()