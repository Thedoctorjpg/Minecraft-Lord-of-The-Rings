"""
Set up full Minecraft profiles for LOTR Legacy 1.7.10 + Forge + LOTRO resource pack.

Creates:
  - Vanilla 1.7.10 + Forge 10.13.4.1614 in %APPDATA%/.minecraft/versions/
  - Isolated game dir: %APPDATA%/.minecraft/profiles/lotr-legacy-1710/
  - Mods, resource pack, options with pack pre-enabled
  - Launcher profile + direct-launch .bat for testing

Usage:
    python setup_profiles.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
MC = Path.home() / "AppData" / "Roaming" / ".minecraft"
MOD_JAR_SRC = TOOLS / "mod_cache" / "LOTRModfork.v36.35.jar"
FORGE_INSTALLER_URL = (
    "https://maven.minecraftforge.net/net/minecraftforge/forge/"
    "1.7.10-10.13.4.1614-1.7.10/forge-1.7.10-10.13.4.1614-1.7.10-installer.jar"
)
FORGE_VERSION_ID = "1.7.10-Forge10.13.4.1614-1.7.10"
FORGE_LIB_PATH = (
    "net/minecraftforge/forge/1.7.10-10.13.4.1614-1.7.10/"
    "forge-1.7.10-10.13.4.1614-1.7.10-universal.jar"
)
PROFILE_ID = "lotr-legacy-1710"
PROFILE_NAME = "LOTR Legacy + LOTRO Pack"
GAME_DIR = MC / "profiles" / PROFILE_ID
PACK_TEST_ID = "lotro-pack-test-1710"
PACK_TEST_NAME = "LOTRO Pack Test (1.7.10 vanilla)"
PACK_TEST_DIR = MC / "profiles" / PACK_TEST_ID
JAVA8 = Path(r"D:\jre\bin\java.exe")
PACK_ZIP = MC / "resourcepacks" / "lotr-minecraft-to-lotro-upgrade.zip"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    print(f"  download: {dest.name}")
    req = urllib.request.Request(url, headers={"User-Agent": "lotr-profile-setup/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def install_minecraft_1710() -> None:
    manifest = json.loads(
        urllib.request.urlopen(
            "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=30
        ).read()
    )
    entry = next(v for v in manifest["versions"] if v["id"] == "1.7.10")
    version_json = json.loads(urllib.request.urlopen(entry["url"], timeout=30).read())

    ver_dir = MC / "versions" / "1.7.10"
    ver_dir.mkdir(parents=True, exist_ok=True)
    json_path = ver_dir / "1.7.10.json"
    jar_path = ver_dir / "1.7.10.jar"

    if not json_path.exists():
        json_path.write_text(json.dumps(version_json, indent=2), encoding="utf-8")

    if not jar_path.exists():
        client = version_json["downloads"]["client"]
        download(client["url"], jar_path)

    # Legacy assets index for 1.7.10
    if "assetIndex" in version_json:
        assets_dir = MC / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        indexes_dir = assets_dir / "indexes"
        indexes_dir.mkdir(exist_ok=True)
        idx = version_json["assetIndex"]
        idx_path = indexes_dir / f"{idx['id']}.json"
        if not idx_path.exists():
            download(idx["url"], idx_path)


def install_forge() -> None:
    installer = TOOLS / "mod_cache" / "forge-1.7.10-installer.jar"
    download(FORGE_INSTALLER_URL, installer)

    forge_dir = MC / "versions" / FORGE_VERSION_ID
    forge_json = forge_dir / f"{FORGE_VERSION_ID}.json"
    if forge_json.exists():
        print(f"  forge already installed: {FORGE_VERSION_ID}")
        return

    java = str(JAVA8 if JAVA8.exists() else shutil.which("java") or "java")
    extract_dir = TOOLS / "mod_cache" / "forge_extract"
    universal = extract_dir / "forge-1.7.10-10.13.4.1614-1.7.10-universal.jar"

    if not universal.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        print("  extracting Forge universal jar...")
        subprocess.run([java, "-jar", str(installer), "--extract"], cwd=str(extract_dir), check=True)

    with zipfile.ZipFile(installer) as zf:
        profile = json.loads(zf.read("install_profile.json"))
    version_info = profile["versionInfo"]

    forge_dir.mkdir(parents=True, exist_ok=True)
    forge_json.write_text(json.dumps(version_info, indent=2), encoding="utf-8")

    lib_dest = MC / "libraries" / Path(*FORGE_LIB_PATH.split("/"))
    lib_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(universal, lib_dest)
    print(f"  installed forge version: {FORGE_VERSION_ID}")


def stage_production_pack() -> None:
    staging = TOOLS / "_pack_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    shutil.copy2(ROOT / "pack.mcmeta", staging / "pack.mcmeta")
    shutil.copytree(ROOT / "assets", staging / "assets")

    PACK_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if PACK_ZIP.exists():
        PACK_ZIP.unlink()
    shutil.make_archive(str(PACK_ZIP.with_suffix("")), "zip", staging)
    shutil.rmtree(staging)


def setup_game_profile() -> None:
    GAME_DIR.mkdir(parents=True, exist_ok=True)
    mods = GAME_DIR / "mods"
    mods.mkdir(exist_ok=True)
    rp = GAME_DIR / "resourcepacks"
    rp.mkdir(exist_ok=True)

    dest_mod = mods / "LOTRModfork.v36.35.jar"
    if not dest_mod.exists():
        shutil.copy2(MOD_JAR_SRC, dest_mod)

    dest_pack = rp / "lotr-minecraft-to-lotro-upgrade.zip"
    if PACK_ZIP.exists():
        shutil.copy2(PACK_ZIP, dest_pack)
    elif not dest_pack.exists() and (MC / "resourcepacks" / "lotr-minecraft-to-lotro-upgrade.zip").exists():
        shutil.copy2(MC / "resourcepacks" / "lotr-minecraft-to-lotro-upgrade.zip", dest_pack)

    # 1.7.10 resourcePacks option uses folder/zip name in older format
    options = GAME_DIR / "options.txt"
    pack_ref = "lotr-minecraft-to-lotro-upgrade.zip"
    lines = []
    if options.exists():
        lines = options.read_text(encoding="utf-8", errors="ignore").splitlines()
        lines = [ln for ln in lines if not ln.startswith("resourcePacks:")]
    lines.append(f"resourcePacks:[\"{pack_ref}\"]")
    lines.extend([
        "lang:en_US",
        "soundCategory_master:1.0",
        "renderDistance:12",
        "fancyGraphics:true",
        "particles:2",
    ])
    options.write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = GAME_DIR / "README_PROFILE.txt"
    readme.write_text(
        f"LOTR Legacy 1.7.10 Profile\n"
        f"========================\n"
        f"Forge version: {FORGE_VERSION_ID}\n"
        f"Mod: LOTRModfork.v36.35.jar\n"
        f"Resource pack: {pack_ref}\n\n"
        f"Launch via Minecraft Launcher installation:\n"
        f"  Version: {FORGE_VERSION_ID}\n"
        f"  Game directory: {GAME_DIR}\n\n"
        f"Or double-click: tools/launch_lotr_legacy.bat\n",
        encoding="utf-8",
    )


def setup_pack_test_profile() -> None:
    """Vanilla 1.7.10 — test destroy overlays/sounds without the LOTR mod."""
    PACK_TEST_DIR.mkdir(parents=True, exist_ok=True)
    rp = PACK_TEST_DIR / "resourcepacks"
    rp.mkdir(exist_ok=True)
    if PACK_ZIP.exists():
        shutil.copy2(PACK_ZIP, rp / "lotr-minecraft-to-lotro-upgrade.zip")
    options = PACK_TEST_DIR / "options.txt"
    options.write_text(
        'resourcePacks:["lotr-minecraft-to-lotro-upgrade.zip"]\n'
        "lang:en_US\n",
        encoding="utf-8",
    )


def update_launcher_profiles() -> None:
    profiles_path = MC / "launcher_profiles.json"
    if profiles_path.exists():
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
    else:
        data = {"profiles": {}, "settings": {}, "version": 6}

    data.setdefault("settings", {})
    data["settings"]["enableHistorical"] = True

    profiles = [
        (PROFILE_ID, PROFILE_NAME, FORGE_VERSION_ID, GAME_DIR),
        (PACK_TEST_ID, PACK_TEST_NAME, "1.7.10", PACK_TEST_DIR),
    ]
    for profile_key, name, version_id, game_dir in profiles:
        pid = uuid.uuid5(uuid.NAMESPACE_DNS, profile_key).hex
        data["profiles"][pid] = {
            "created": "2026-06-18T00:00:00.000Z",
            "icon": "Dirt",
            "lastUsed": "2026-06-18T00:00:00.000Z",
            "lastVersionId": version_id,
            "name": name,
            "type": "custom",
            "gameDir": str(game_dir),
            "javaArgs": "-Xms1G -Xmx3G -XX:+UseG1GC",
        }
        print(f"  launcher profile: {name}")

    profiles_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_launch_bat() -> None:
    bat = TOOLS / "launch_lotr_legacy.bat"
    java = str(JAVA8 if JAVA8.exists() else "java")
    bat.write_text(
        f"@echo off\n"
        f"set JAVA=\"{java}\"\n"
        f"set MC=\"{MC}\"\n"
        f"set GAME=\"{GAME_DIR}\"\n"
        f"set VER=\"{FORGE_VERSION_ID}\"\n"
        f"echo Launching LOTR Legacy 1.7.10 + LOTRO pack...\n"
        f"echo Game dir: %GAME%\n"
        f"echo.\n"
        f"echo NOTE: Log in through the official Minecraft Launcher first.\n"
        f"echo Use Installation: {FORGE_VERSION_ID} with game dir above.\n"
        f"pause\n",
        encoding="utf-8",
    )


def write_installation_guide() -> None:
    guide = ROOT / "PROFILES_SETUP.txt"
    guide.write_text(
        "LOTR Legacy — Full Profile Setup\n"
        "================================\n\n"
        f"Forge version : {FORGE_VERSION_ID}\n"
        f"Game directory: {GAME_DIR}\n"
        f"Mod           : LOTRModfork.v36.35.jar\n"
        f"Resource pack : lotr-minecraft-to-lotro-upgrade.zip (enabled)\n\n"
        "PROFILES CREATED\n"
        "----------------\n"
        f"1) {PROFILE_NAME}\n"
        f"   Version: {FORGE_VERSION_ID}\n"
        f"   Game dir: {GAME_DIR}\n\n"
        f"2) {PACK_TEST_NAME}\n"
        f"   Version: 1.7.10 (vanilla — break overlays/sounds only)\n"
        f"   Game dir: {PACK_TEST_DIR}\n\n"
        "MINECRAFT LAUNCHER (recommended)\n"
        "--------------------------------\n"
        "1. Open Minecraft Launcher\n"
        "2. Installations → New installation\n"
        "3. Name: LOTR Legacy + LOTRO Pack\n"
        f"4. Version: {FORGE_VERSION_ID}\n"
        f"5. Game directory: {GAME_DIR}\n"
        "6. JVM arguments: -Xms1G -Xmx3G\n"
        "7. Create → Play\n\n"
        "IF FORGE VERSION NOT IN LIST\n"
        "----------------------------\n"
        "  python tools/setup_profiles.py\n"
        "  Restart launcher\n"
        "  Enable 'Historical versions' in launcher settings if needed\n\n"
        "IN-GAME TEST\n"
        "------------\n"
        "  Options → Resource Packs → pack should be active\n"
        "  Mine stone → LOTRO crack overlay\n"
        "  /give or creative → Rohirric armour, mithril, cracked bricks\n\n"
        "RE-RUN SETUP\n"
        "------------\n"
        "  python tools/setup_profiles.py\n",
        encoding="utf-8",
    )


def main() -> None:
    if not MOD_JAR_SRC.exists():
        raise SystemExit(f"Missing mod JAR: {MOD_JAR_SRC}")

    print("Staging production resource pack zip...")
    stage_production_pack()

    print("Installing Minecraft 1.7.10...")
    install_minecraft_1710()

    print("Installing Forge 1.7.10...")
    install_forge()

    print("Setting up isolated LOTR game profile...")
    setup_game_profile()

    print("Setting up vanilla 1.7.10 pack-test profile...")
    setup_pack_test_profile()

    print("Updating launcher profiles...")
    update_launcher_profiles()

    write_launch_bat()
    write_installation_guide()

    print("\nSetup complete.")
    print(f"  Game dir : {GAME_DIR}")
    print(f"  Forge    : {FORGE_VERSION_ID}")
    print(f"  Guide    : {ROOT / 'PROFILES_SETUP.txt'}")


if __name__ == "__main__":
    main()