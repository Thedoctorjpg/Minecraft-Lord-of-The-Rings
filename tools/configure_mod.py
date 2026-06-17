"""
Switch the resource pack between LOTR Legacy (1.7.10) and Renewed (1.16.5) layouts.

Usage:
    python configure_mod.py renewed
    python configure_mod.py legacy
    python configure_mod.py renewed --mc 1.16.5
    python configure_mod.py legacy  --mc 1.7.10
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROFILES = {
    "renewed": {
        "minecraft_version": "1.16.5",
        "pack_format": 6,
        "mod_loader": "forge",
        "mod_jar_hint": "lotr-1.16-renewed-5.5.jar",
        "texture_roots": {
            "block": "assets/lotr/textures/block",
            "item": "assets/lotr/textures/item",
            "entity": "assets/lotr/textures/entity",
            "gui": "assets/lotr/textures/gui",
        },
        "sounds_root": "assets/lotr/sounds",
        "description_suffix": "§8[Renewed 1.16.5]",
    },
    "legacy": {
        "minecraft_version": "1.7.10",
        "pack_format": 1,
        "mod_loader": "forge",
        "mod_jar_hint": "The-Lord-of-the-Rings-Mod-legacy-*.jar (CurseForge, MC 1.7.10)",
        "texture_roots": {
            "block": "assets/lotr/textures/blocks",
            "item": "assets/lotr/textures/items",
            "entity": "assets/lotr/textures/entity",
            "gui": "assets/lotr/textures/gui",
        },
        "sounds_root": "assets/lotr/sounds",
        "description_suffix": "§8[Legacy 1.7.10]",
    },
}

PACK_FORMAT_BY_MC = {
    "1.7.10": 1,
    "1.12.2": 6,
    "1.16.5": 6,
    "1.18.2": 8,
    "1.19.4": 13,
    "1.20.1": 15,
    "1.20.4": 32,
    "1.20.6": 34,
    "1.21": 48,
    "1.21.1": 48,
}


def write_pack_mcmeta(branch: str, pack_format: int) -> None:
    suffix = PROFILES[branch]["description_suffix"]
    content = {
        "pack": {
            "pack_format": pack_format,
            "description": (
                "§6LOTR Minecraft → LOTRO Resource Upgrade\n"
                "§7Higher fidelity textures, ores, armor & sounds inspired by LOTRO\n"
                f"{suffix}"
            ),
        }
    }
    (ROOT / "pack.mcmeta").write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def ensure_dirs(branch: str) -> list[str]:
    created: list[str] = []
    for rel in PROFILES[branch]["texture_roots"].values():
        path = ROOT / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel)
    sounds = ROOT / PROFILES[branch]["sounds_root"]
    if not sounds.exists():
        sounds.mkdir(parents=True, exist_ok=True)
        created.append(PROFILES[branch]["sounds_root"])
    return created


def write_mod_target(branch: str, mc_version: str, pack_format: int) -> None:
    profile = PROFILES[branch]
    payload = {
        "mod_branch": branch,
        "minecraft_version": mc_version,
        "pack_format": pack_format,
        "mod_loader": profile["mod_loader"],
        "mod_jar_hint": profile["mod_jar_hint"],
        "texture_roots": profile["texture_roots"],
        "sounds_root": profile["sounds_root"],
        "notes": (
            f"Active profile: {branch}. Texture overrides must mirror paths inside the mod JAR. "
            "Extract with: python tools/extract_mod_textures.py <path-to-mod.jar>"
        ),
    }
    (ROOT / "mod_target.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure pack for LOTR Legacy or Renewed.")
    parser.add_argument("branch", choices=["renewed", "legacy"], help="Which LOTR mod branch to target")
    parser.add_argument("--mc", help="Override Minecraft version (e.g. 1.16.5, 1.7.10)")
    args = parser.parse_args()

    profile = PROFILES[args.branch]
    mc_version = args.mc or profile["minecraft_version"]
    pack_format = PACK_FORMAT_BY_MC.get(mc_version, profile["pack_format"])

    write_pack_mcmeta(args.branch, pack_format)
    created = ensure_dirs(args.branch)
    write_mod_target(args.branch, mc_version, pack_format)

    print(f"Configured for LOTR {args.branch.upper()} ({mc_version}, pack_format={pack_format})")
    print(f"Mod JAR hint: {profile['mod_jar_hint']}")
    print("Texture roots:")
    for kind, rel in profile["texture_roots"].items():
        print(f"  {kind}: {rel}")
    if created:
        print("Created directories:")
        for rel in created:
            print(f"  + {rel}")
    print("\nNext: install the matching Forge instance, drop textures in the paths above, zip, enable in-game.")


if __name__ == "__main__":
    main()