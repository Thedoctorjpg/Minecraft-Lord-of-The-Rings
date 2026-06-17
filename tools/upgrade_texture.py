"""
Batch upscale + sharpen textures for the LOTRO-inspired resource pack.

Usage:
    pip install Pillow
    python upgrade_texture.py --input ../source_textures --output ../assets/lotr/textures/block
    python upgrade_texture.py --input old.png --output upgraded.png --scale 4
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def upgrade_texture(
    input_path: Path,
    output_path: Path,
    scale: int = 4,
    contrast: float = 1.3,
    sharpen: bool = True,
) -> None:
    img = Image.open(input_path).convert("RGBA")
    new_size = (img.width * scale, img.height * scale)
    img = img.resize(new_size, Image.LANCZOS)

    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)

    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def iter_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []
    return sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Upscale LOTR mod textures for LOTRO-style fidelity.")
    parser.add_argument("--input", "-i", required=True, help="Source file or folder")
    parser.add_argument("--output", "-o", required=True, help="Output file or folder")
    parser.add_argument("--scale", "-s", type=int, default=4, help="Upscale factor (default: 4)")
    parser.add_argument("--contrast", "-c", type=float, default=1.3, help="Contrast boost (default: 1.3)")
    parser.add_argument("--no-sharpen", action="store_true", help="Skip sharpen pass")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    sharpen = not args.no_sharpen

    if input_path.is_file():
        upgrade_texture(input_path, output_path, args.scale, args.contrast, sharpen)
        print(f"Upgraded: {input_path} -> {output_path}")
        return

    if not input_path.is_dir():
        raise SystemExit(f"Input path not found: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    sources = iter_inputs(input_path)
    if not sources:
        raise SystemExit(f"No supported images found in {input_path}")

    for src in sources:
        rel = src.relative_to(input_path)
        dst = output_path / rel
        upgrade_texture(src, dst, args.scale, args.contrast, sharpen)
        print(f"Upgraded: {rel}")

    print(f"Done. {len(sources)} texture(s) written to {output_path}")


if __name__ == "__main__":
    main()