"""
Build the FULL destructible environment kit from LOTR Legacy mod JAR v36.35.

- All 44 mod-registered *Cracked block textures (exact filenames)
- Dwarven ithildin door glow panels (Moria gates)
- destroy_stage_0..9 break overlays
- Vanilla dig/step/break .ogg + lotr block break sounds + sounds.json

Usage:
    python build_full_destructible_kit.py
    python build_full_destructible_kit.py --skip-sounds
"""

from __future__ import annotations

import json
import math
import random
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
MOD_JAR = TOOLS / "mod_cache" / "LOTRModfork.v36.35.jar"
MC_ASSETS_API = (
    "https://api.github.com/repos/InventivetalentDev/minecraft-assets/contents"
    "/assets/minecraft/sounds/{folder}?ref=1.7.10"
)
MC_SOUND_FOLDERS = ("dig", "step", "random")
EXTRACT_ROOT = ROOT / "source_textures" / "mod_v36.35"
INDEX_OUT = TOOLS / "cracked_block_index.json"

STYLE = {
    "crack_color": [210, 200, 185, 220],
    "dust_tint": [1.02, 0.98, 0.92],
    "weathering": 0.9,
    "contrast": 1.25,
    "rune_lum_threshold": 48,
    "rune_bright_threshold": 115,
    "moon_glow_color": [200, 230, 255, 38],
    "ithildin_glow_color": [220, 240, 255, 45],
}


def jar_entries(jar: Path) -> list[str]:
    with zipfile.ZipFile(jar) as zf:
        return zf.namelist()


def extract_prefix(jar: Path, prefix: str, dest: Path, *, predicate=None) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    seen: set[str] = set()
    with zipfile.ZipFile(jar) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name.startswith(prefix) or info.is_dir():
                continue
            base = Path(name).name
            if base in seen:
                continue
            if predicate and not predicate(name):
                continue
            seen.add(base)
            out = dest / base
            out.write_bytes(zf.read(info))
            extracted.append(base)
    return sorted(extracted)


def make_crack_overlay(size: int, stage: int, rng: random.Random) -> Image.Image:
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    t = (stage + 1) / 10.0
    for _ in range(int(2 + stage * 2.5)):
        x1, y1 = rng.randint(0, size - 1), rng.randint(0, size - 1)
        angle = rng.random() * math.pi
        length = rng.randint(int(size * 0.25), int(size * (0.5 + t * 0.45)))
        x2 = int(x1 + math.cos(angle) * length)
        y2 = int(y1 + math.sin(angle) * length)
        alpha = int(140 + t * 100)
        draw.line((x1, y1, x2, y2), fill=(210, 200, 185, min(255, alpha)), width=1 if stage < 4 else 2)
    return overlay


def write_destroy_stages() -> int:
    out = ROOT / "assets" / "minecraft" / "textures" / "blocks"
    out.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        rng = random.Random(42000 + i * 97)
        make_crack_overlay(16, i, rng).save(out / f"destroy_stage_{i}.png")
    return 10


def is_rune_pixel(r: int, g: int, b: int, lum: float) -> bool:
    return lum >= STYLE["rune_bright_threshold"] or (
        lum >= STYLE["rune_lum_threshold"] and b >= r * 0.85 and g >= r * 0.8
    )


def moon_rune_color(r: int, g: int, b: int, a: int, *, intense: bool = False) -> tuple[int, int, int]:
    if a < 16:
        return r, g, b
    lum = (r + g + b) / 3.0
    factor = STYLE["weathering"] - (0.1 if intense else 0.0)
    if is_rune_pixel(r, g, b, lum):
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


def apply_glow_overlay(img: Image.Image, glow: list[int], threshold: int) -> Image.Image:
    rgba = img.convert("RGBA")
    layer = Image.new("RGBA", rgba.size, tuple(glow))
    mask = rgba.convert("L").point(lambda p: 255 if p > threshold else 0)
    shimmer = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    shimmer.paste(layer, (0, 0), mask)
    return Image.alpha_composite(rgba, shimmer)


def process_pixels(img: Image.Image, mode: str) -> Image.Image:
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    intense = mode == "ithildin_door"
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            nr, ng, nb = moon_rune_color(r, g, b, a, intense=intense)
            pixels[x, y] = (nr, ng, nb, a)
    rgba = ImageEnhance.Contrast(rgba).enhance(STYLE["contrast"] + (0.15 if mode == "ithildin_door" else 0))
    rgba = rgba.filter(ImageFilter.SHARPEN)
    glow = STYLE["ithildin_glow_color"] if mode == "ithildin_door" else STYLE["moon_glow_color"]
    return apply_glow_overlay(rgba, glow, 85 if mode == "ithildin_door" else 100)


def enhance_cracked(img: Image.Image, seed: int) -> Image.Image:
    rng = random.Random(seed)
    rgba = img.convert("RGBA")
    dust = STYLE["dust_tint"]
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a < 16:
                continue
            r = int(r * STYLE["weathering"] * dust[0])
            g = int(g * STYLE["weathering"] * dust[1])
            b = int(b * STYLE["weathering"] * dust[2])
            pixels[x, y] = (min(255, r), min(255, g), min(255, b), a)
    rgba = ImageEnhance.Contrast(rgba).enhance(STYLE["contrast"])
    crack = make_crack_overlay(rgba.width, 4, rng)
    if rgba.width != crack.width:
        crack = crack.resize(rgba.size, Image.NEAREST)
    return Image.alpha_composite(rgba, crack)


def upgrade_cracked_blocks(names: list[str]) -> int:
    src_dir = EXTRACT_ROOT / "blocks" / "cracked"
    out_dir = ROOT / "assets" / "lotr" / "textures" / "blocks"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in names:
        src = src_dir / name
        if not src.exists():
            continue
        enhanced = enhance_cracked(Image.open(src), seed=hash(name) % 100000)
        enhanced.save(out_dir / name)
        count += 1
    return count


def upgrade_ithildin_doors(names: list[str]) -> int:
    src_dir = EXTRACT_ROOT / "blocks" / "ithildin_doors"
    out_dir = ROOT / "assets" / "lotr" / "textures" / "blocks"
    count = 0
    for name in names:
        src = src_dir / name
        if not src.exists():
            continue
        process_pixels(Image.open(src), "ithildin_door").save(out_dir / name)
        count += 1
    return count


def download_vanilla_sounds_1710() -> list[str]:
    """Pull MC 1.7.10 dig/step/break .ogg from InventivetalentDev/minecraft-assets."""
    out = ROOT / "assets" / "minecraft" / "sounds"
    copied: list[str] = []
    headers = {"User-Agent": "lotr-destructible-kit"}

    for folder in MC_SOUND_FOLDERS:
        api = MC_ASSETS_API.format(folder=folder)
        req = urllib.request.Request(api, headers=headers)
        try:
            entries = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as exc:
            print(f"  warn: could not list {folder}: {exc}")
            continue
        for entry in entries:
            name = entry.get("name", "")
            if not name.endswith(".ogg"):
                continue
            url = entry.get("download_url")
            if not url:
                continue
            rel = f"{folder}/{name}"
            dest = out / folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                copied.append(rel.replace(".ogg", ""))
                continue
            urllib.request.urlretrieve(url, dest)
            copied.append(rel.replace(".ogg", ""))
    return copied


def extract_lotr_break_sounds() -> list[str]:
    out = ROOT / "assets" / "lotr" / "sounds"
    copied: list[str] = []
    with zipfile.ZipFile(MOD_JAR) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name.startswith("assets/lotr/sounds/") or not name.endswith(".ogg"):
                continue
            if not any(k in name.lower() for k in ("break", "dig", "step", "plate", "treasure")):
                continue
            rel = name.split("assets/lotr/sounds/", 1)[1]
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info))
            copied.append(f"lotr:{rel.replace('.ogg', '')}")
    return copied


def write_sounds_json(vanilla_events: list[str]) -> None:
    """Map vanilla dig/step events to extracted .ogg paths."""
    events: dict[str, dict] = {}
    groups = {
        "dig/stone": [f"dig/stone{i}" for i in range(1, 5)],
        "dig/wood": [f"dig/wood{i}" for i in range(1, 5)],
        "dig/gravel": [f"dig/gravel{i}" for i in range(1, 5)],
        "dig/grass": [f"dig/grass{i}" for i in range(1, 5)],
        "dig/sand": [f"dig/sand{i}" for i in range(1, 5)],
        "dig/snow": [f"dig/snow{i}" for i in range(1, 5)],
        "step/stone": [f"step/stone{i}" for i in range(1, 7)],
        "step/wood": [f"step/wood{i}" for i in range(1, 7)],
        "random/break": [f"random/break{i}" for i in range(1, 4)],
    }
    available = set(vanilla_events)
    for event, candidates in groups.items():
        sounds = [c for c in candidates if c in available]
        if sounds:
            events[event] = {"category": "block", "sounds": sounds}
    path = ROOT / "assets" / "minecraft" / "sounds.json"
    path.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")


def discover_and_extract() -> dict:
    if not MOD_JAR.exists():
        raise SystemExit(f"Mod JAR missing: {MOD_JAR}")

    cracked = extract_prefix(
        MOD_JAR,
        "assets/lotr/textures/blocks/",
        EXTRACT_ROOT / "blocks" / "cracked",
        predicate=lambda n: "cracked" in n.lower(),
    )
    ithildin_doors = extract_prefix(
        MOD_JAR,
        "assets/lotr/textures/blocks/",
        EXTRACT_ROOT / "blocks" / "ithildin_doors",
        predicate=lambda n: "dwarvendoorithildin_glow" in n.lower(),
    )
    return {"cracked": cracked, "ithildin_doors": ithildin_doors}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build full LOTRO destructible environment kit")
    parser.add_argument("--skip-sounds", action="store_true")
    args = parser.parse_args()

    print(f"Using mod JAR: {MOD_JAR.name}")
    data = discover_and_extract()
    INDEX_OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(data['cracked'])} cracked blocks, {len(data['ithildin_doors'])} ithildin door panels")

    print("Generating destroy_stage overlays...")
    stages = write_destroy_stages()

    print("Upgrading cracked stonework...")
    cracked_n = upgrade_cracked_blocks(data["cracked"])

    print("Upgrading ithildin door glow panels...")
    door_n = upgrade_ithildin_doors(data["ithildin_doors"])

    sound_n = 0
    if not args.skip_sounds:
        print("Downloading MC 1.7.10 dig/step/break sounds...")
        vanilla = download_vanilla_sounds_1710()
        write_sounds_json(vanilla)
        sound_n = len(vanilla)
        lotr_s = extract_lotr_break_sounds()
        print(f"  vanilla .ogg files: {sound_n}, lotr break sounds: {len(lotr_s)}")

    # Update mod_target with jar path
    target = json.loads((ROOT / "mod_target.json").read_text(encoding="utf-8"))
    target["mod_jar_local"] = str(MOD_JAR)
    target["mod_version"] = "v36.35 (quentin452 fork)"
    target["destructible_kit"] = {
        "cracked_blocks": len(data["cracked"]),
        "ithildin_door_panels": len(data["ithildin_doors"]),
        "destroy_stages": stages,
        "sound_events": sound_n,
    }
    (ROOT / "mod_target.json").write_text(json.dumps(target, indent=2) + "\n", encoding="utf-8")

    total = stages + cracked_n + door_n
    print(f"\nFull kit ready — {total} textures + {sound_n} sound files")
    print(f"Cracked index: {INDEX_OUT.relative_to(ROOT)}")
    print("Zip pack -> 1.7.10 Forge resourcepacks/ and mine Middle-earth stone!")


if __name__ == "__main__":
    main()