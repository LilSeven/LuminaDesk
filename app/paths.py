"""Application-wide constants and filesystem locations."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LuminaDesk"
APP_DISPLAY_NAME = "Lumina Desk"
APP_NAME_ZH = "暮光桌面"
VERSION = "1.1.1"
REPO_URL = "https://github.com/LilSeven/LuminaDesk"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_path(*parts: str) -> Path:
    """Locate a bundled asset both in development and inside the exe."""
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def data_dir() -> Path:
    """Per-user writable directory for config, notes and logs."""
    override = os.environ.get("LUMINA_DATA_DIR")
    if override:
        path = Path(override)
    else:
        appdata = os.environ.get("APPDATA")
        path = Path(appdata) / APP_NAME if appdata else Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path
