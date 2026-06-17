"""
Extract LOTR mod textures from a mod JAR into source_textures/ for upgrading.

Usage:
    python extract_mod_textures.py "C:\\path\\to\\lotr-1.16-renewed-5.5.jar"
    python extract_mod_textures.py mod.jar --filter mithril
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXTURE_MARKERS = ("/textures/", "\\textures\\")
IMAGE_EXTENSIONS = (".png", ".mcmeta")


def load_target() -> dict:
    target_file = ROOT / "mod_target.json"
    if not target_file.exists():
        raise SystemExit("mod_target.json missing. Run: python tools/configure_mod.py renewed")
    return json.loads(target_file.read_text(encoding="utf-8"))


def is_texture_path(path: str) -> bool:
    lower = path.lower()
    return any(marker in lower for marker in TEXTURE_MARKERS) and lower.endswith(IMAGE_EXTENSIONS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract textures from a LOTR mod JAR.")
    parser.add_argument("jar", help="Path to LOTR mod .jar")
    parser.add_argument("--filter", "-f", help="Only extract paths containing this substring (e.g. mithril)")
    parser.add_argument("--output", "-o", default=str(ROOT / "source_textures"), help="Output folder")
    args = parser.parse_args()

    jar_path = Path(args.jar)
    if not jar_path.is_file():
        raise SystemExit(f"JAR not found: {jar_path}")

    target = load_target()
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    extracted = 0
    with zipfile.ZipFile(jar_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if not is_texture_path(name):
                continue
            if not name.startswith("assets/lotr/"):
                continue
            if args.filter and args.filter.lower() not in name.lower():
                continue

            rel = Path(*Path(name).parts[2:])  # strip assets/lotr/
            dest = output_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info))
            extracted += 1

    print(f"Branch: {target['mod_branch']} ({target['minecraft_version']})")
    print(f"Extracted {extracted} file(s) to {output_root}")
    if extracted:
        print("Upscale with:")
        block_root = target["texture_roots"]["block"]
        print(f'  python tools/upgrade_texture.py -i "{output_root}" -o "{ROOT / block_root}"')


if __name__ == "__main__":
    main()