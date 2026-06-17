"""Download Rohan armour base textures (stdlib only — no Pillow)."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).with_name("rohan_armor_manifest.json")
SOURCE_DIR = ROOT / "source_textures" / "rohan"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = list(manifest["armor"]) + list(manifest.get("weapons", []))
    base_url = manifest["base_url"].rstrip("/")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    for name in targets:
        dest = SOURCE_DIR / name
        if dest.exists():
            print(f"skip: {name}")
            continue
        url = f"{base_url}/{name}"
        print(f"fetch: {name}")
        urllib.request.urlretrieve(url, dest)

    print(f"Saved to {SOURCE_DIR}")


if __name__ == "__main__":
    main()