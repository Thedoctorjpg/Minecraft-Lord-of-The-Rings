"""
LOTRO-style destructible environment visuals for Legacy 1.7.10.

- Custom destroy_stage_0..9 break overlays (minecraft namespace)
- Ruined / cracked Middle-earth stonework variants (lotr namespace)
- sounds.json scaffold for heavier dig/break SFX (add .ogg files to enable)

Usage:
    python upgrade_destructible_env.py
    python upgrade_destructible_env.py --stages-only
    python upgrade_destructible_env.py --ruins-only
"""

from __future__ import annotations

import argparse
import json
import math
import random
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name("destructible_manifest.json")
SOURCE = ROOT / "source_textures" / "destructible"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def fetch_lotr(manifest: dict, rel: str, dest: Path) -> bool:
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


def make_crack_overlay(size: int, stage: int, rng: random.Random) -> Image.Image:
    """Transparent overlay with crack lines; stage 0=light, 9=heavy."""
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    t = (stage + 1) / 10.0
    line_count = int(2 + stage * 2.5)
    for _ in range(line_count):
        x1, y1 = rng.randint(0, size - 1), rng.randint(0, size - 1)
        angle = rng.random() * math.pi
        length = rng.randint(int(size * 0.25), int(size * (0.5 + t * 0.45)))
        x2 = int(x1 + math.cos(angle) * length)
        y2 = int(y1 + math.sin(angle) * length)
        width = 1 if stage < 4 else 2
        alpha = int(140 + t * 100)
        draw.line((x1, y1, x2, y2), fill=(210, 200, 185, min(255, alpha)), width=width)
        draw.line((x1 + 1, y1, x2 + 1, y2), fill=(80, 70, 65, int(alpha * 0.6)), width=1)
    if stage >= 5:
        for _ in range(int(stage - 3)):
            cx, cy = rng.randint(2, size - 3), rng.randint(2, size - 3)
            r = rng.randint(1, 2 + stage // 3)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(180, 170, 160, 200))
    return overlay


def generate_destroy_stages(count: int, size: int = 16) -> list[Image.Image]:
    stages: list[Image.Image] = []
    for i in range(count):
        rng = random.Random(42000 + i * 97)
        overlay = make_crack_overlay(size, i, rng)
        if i >= 3:
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.4))
        stages.append(overlay)
    return stages


def apply_weathering(img: Image.Image, style: dict, severity: float) -> Image.Image:
    rgba = img.convert("RGBA")
    dust = style["dust_tint"]
    w = style["weathering"] - severity * 0.15
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a < 16:
                continue
            r = int(r * w * dust[0])
            g = int(g * w * dust[1])
            b = int(b * w * dust[2])
            pixels[x, y] = (min(255, r), min(255, g), min(255, b), a)
    return ImageEnhance.Contrast(rgba).enhance(1.15 + severity * 0.2)


def apply_ruin(base: Image.Image, severity: float, style: dict, seed: int) -> Image.Image:
    size = base.size[0]
    rng = random.Random(seed)
    ruined = apply_weathering(base, style, severity)
    stage = min(9, int(severity * 12))
    crack = make_crack_overlay(size, stage, rng)
    ruined = Image.alpha_composite(ruined.convert("RGBA"), crack)
    return ruined.filter(ImageFilter.SHARPEN)


def write_destroy_stages(manifest: dict) -> int:
    out_dir = ROOT / "assets" / "minecraft" / "textures" / "blocks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stages = generate_destroy_stages(manifest["destroy_stages"])
    for i, img in enumerate(stages):
        path = out_dir / f"destroy_stage_{i}.png"
        img.save(path)
        print(f"  destroy_stage_{i}.png")
    return len(stages)


def lotr_block_output(rel: str) -> Path:
    return ROOT / "assets" / "lotr" / "textures" / "blocks" / Path(rel).name


def write_ruins(manifest: dict, download: bool) -> int:
    style = manifest["lotro_style"]
    count = 0

    if download:
        print("Downloading stonework bases...")
        for rel in manifest["ruin_enhance"]:
            fetch_lotr(manifest, rel, SOURCE / rel)
        for entry in manifest["ruin_derive"]:
            fetch_lotr(manifest, entry["source"], SOURCE / entry["source"])

    print("Generating ruined stonework...")
    for rel in manifest["ruin_enhance"]:
        src = SOURCE / rel
        if not src.exists():
            print(f"  missing: {rel}")
            continue
        base = Image.open(src)
        ruined = apply_ruin(base, 0.65, style, seed=hash(rel) % 10000)
        dest = lotr_block_output(rel)
        ruined.save(dest)
        print(f"  enhanced: {dest.name}")
        count += 1

    for i, entry in enumerate(manifest["ruin_derive"]):
        src = SOURCE / entry["source"]
        if not src.exists():
            print(f"  missing source: {entry['source']}")
            continue
        base = Image.open(src)
        ruined = apply_ruin(base, entry["severity"], style, seed=9000 + i)
        dest = lotr_block_output(entry["output"])
        ruined.save(dest)
        print(f"  derived: {dest.name}")
        count += 1

    return count


def write_sounds_scaffold() -> None:
    sounds_dir = ROOT / "assets" / "minecraft" / "sounds" / "dig"
    sounds_dir.mkdir(parents=True, exist_ok=True)
    readme = sounds_dir / "README_ADD_OGG_HERE.txt"
    readme.write_text(
        "Drop LOTRO-style dig sounds here to override vanilla breaks:\n"
        "  stone1.ogg, stone2.ogg, stone3.ogg, stone4.ogg\n"
        "  wood1.ogg, wood2.ogg, wood3.ogg, wood4.ogg\n"
        "  gravel1.ogg ... sand1.ogg ...\n"
        "Then enable sounds.json in assets/minecraft/.\n",
        encoding="utf-8",
    )

    sounds_json = ROOT / "assets" / "minecraft" / "sounds.json"
    if sounds_json.exists():
        return

    # Scaffold only — entries activate once .ogg files are added.
    payload = {
        "dig/stone1": {"category": "block", "sounds": ["dig/stone1"]},
        "dig/stone2": {"category": "block", "sounds": ["dig/stone2"]},
        "dig/stone3": {"category": "block", "sounds": ["dig/stone3"]},
        "dig/stone4": {"category": "block", "sounds": ["dig/stone4"]},
    }
    sounds_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("  sounds.json scaffold (add .ogg to assets/minecraft/sounds/dig/)")


def main() -> None:
    parser = argparse.ArgumentParser(description="LOTRO destructible environment upgrade")
    parser.add_argument("--stages-only", action="store_true")
    parser.add_argument("--ruins-only", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    total = 0

    if not args.ruins_only:
        print("Generating break-crack overlays...")
        total += write_destroy_stages(manifest)
        write_sounds_scaffold()

    if not args.stages_only:
        total += write_ruins(manifest, download=not args.no_download)

    print(f"\nDone — {total} destructible asset(s).")
    print("Mine LOTR stone/bricks to see custom crack overlays; use ruined blocks for battle-scarred builds.")


if __name__ == "__main__":
    main()