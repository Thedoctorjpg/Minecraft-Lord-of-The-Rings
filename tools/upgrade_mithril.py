"""
Download and LOTRO-grade mithril textures for Legacy 1.7.10.

LOTRO mithril: cool blue-silver shimmer, luminous highlights, deep blue shadows.

Usage:
    python upgrade_mithril.py
    python upgrade_mithril.py --no-download
    python upgrade_mithril.py --armor-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name("mithril_manifest.json")
SOURCE = ROOT / "source_textures" / "mithril"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def fetch_asset(manifest: dict, rel: str, dest: Path) -> None:
    url = f"{manifest['base_repo']}/assets/lotr/{rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    print(f"  fetch: {rel}")
    urllib.request.urlretrieve(url, dest)


def download_all(manifest: dict, targets: list[str]) -> None:
    print("Downloading base mithril textures...")
    for rel in targets:
        fetch_asset(manifest, rel, SOURCE / rel)
        mcmeta_rel = f"{rel}.mcmeta"
        try:
            fetch_asset(manifest, mcmeta_rel, SOURCE / mcmeta_rel)
        except Exception:
            pass


def lotro_mithril_color(r: int, g: int, b: int, a: int, style: dict) -> tuple[int, int, int]:
    if a < 16:
        return r, g, b

    lum = (r + g + b) / 3.0

    if lum >= style["glow_threshold"]:
        r = min(255, int(r * style["highlight_red_scale"] + 8))
        g = min(255, int(g * style["silver_green_boost"] + 18))
        b = min(255, int(b * style["highlight_blue_boost"] + 30))
    elif lum > 70:
        r = min(255, int(r * 0.88))
        g = min(255, int(g * 1.04 + 4))
        b = min(255, int(b * 1.18 + 10))
    else:
        r = max(0, int(r * 0.72))
        g = max(0, int(g * 0.82))
        b = min(255, int(b * style["shadow_blue_depth"] + 6))

    return r, g, b


def apply_mithril_grade(img: Image.Image, style: dict) -> Image.Image:
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            nr, ng, nb = lotro_mithril_color(r, g, b, a, style)
            pixels[x, y] = (nr, ng, nb, a)

    rgba = ImageEnhance.Contrast(rgba).enhance(style["contrast"])
    rgba = rgba.filter(ImageFilter.SHARPEN)

    glow = Image.new("RGBA", rgba.size, tuple(style["glow_color"]))
    mask = rgba.convert("L").point(lambda p: 255 if p > style["glow_threshold"] else 0)
    shimmer = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    shimmer.paste(glow, (0, 0), mask)
    return Image.alpha_composite(rgba, shimmer)


def is_vertical_sheet(path: Path) -> bool:
    mcmeta = path.with_suffix(path.suffix + ".mcmeta")
    if mcmeta.exists():
        return True
    with Image.open(path) as img:
        w, h = img.size
        return h > w and h % w == 0 and h // w >= 4


def upgrade_image(src: Path, dest: Path, style: dict) -> None:
    img = Image.open(src)
    if is_vertical_sheet(src):
        w, h = img.size
        frame_h = w
        frames = h // frame_h
        out = Image.new("RGBA", (w, h))
        for i in range(frames):
            box = (0, i * frame_h, w, (i + 1) * frame_h)
            frame = img.crop(box)
            out.paste(apply_mithril_grade(frame, style), box)
        result = out
    else:
        result = apply_mithril_grade(img, style)

    dest.parent.mkdir(parents=True, exist_ok=True)
    result.save(dest)

    mcmeta_src = src.with_suffix(src.suffix + ".mcmeta")
    if mcmeta_src.exists():
        shutil.copy2(mcmeta_src, dest.with_suffix(dest.suffix + ".mcmeta"))


def output_path(rel: str) -> Path:
    if rel.startswith("textures/items/"):
        name = Path(rel).name
        return ROOT / "assets" / "lotr" / "textures" / "items" / name
    if rel.startswith("textures/blocks/"):
        name = Path(rel).name
        return ROOT / "assets" / "lotr" / "textures" / "blocks" / name
    if rel.startswith("armor/"):
        name = Path(rel).name
        return ROOT / "assets" / "lotr" / "armor" / name
    raise ValueError(f"Unknown asset path: {rel}")


def collect_targets(manifest: dict, armor_only: bool, resources_only: bool) -> list[str]:
    items = list(manifest["items"])
    blocks = list(manifest["blocks"])
    armor = list(manifest["armor_layers"])

    if armor_only:
        return armor
    if resources_only:
        return [t for t in items if "mithril.png" in t or "Nugget" in t or "Ring" in t or "Book" in t] + blocks
    return items + blocks + armor


def main() -> None:
    parser = argparse.ArgumentParser(description="LOTRO-style mithril upgrade for Legacy 1.7.10")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--armor-only", action="store_true")
    parser.add_argument("--resources-only", action="store_true", help="Ingots, nuggets, bars only")
    args = parser.parse_args()

    manifest = load_manifest()
    style = manifest["lotro_style"]
    targets = collect_targets(manifest, args.armor_only, args.resources_only)

    if not args.no_download:
        download_all(manifest, targets)

    upgraded = 0
    print("Upgrading mithril textures...")
    for rel in targets:
        src = SOURCE / rel
        if not src.exists():
            print(f"  missing: {rel}")
            continue
        dest = output_path(rel)
        upgrade_image(src, dest, style)
        print(f"  upgraded: {rel} -> {dest.relative_to(ROOT)}")
        upgraded += 1

    print(f"\nDone — {upgraded} mithril texture(s) ready.")
    print("Animated items keep .mcmeta shimmer. Test ingot + full mithril armour in 1.7.10.")


if __name__ == "__main__":
    main()