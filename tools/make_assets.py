"""Generate the app icon (.png/.ico) from the Qt vector artwork."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PIL import Image  # noqa: E402

from app.ui.icons import app_pixmap  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)  # noqa: F841  (QPixmap needs a GUI app)
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)

    large = assets / "icon.png"
    if not app_pixmap(512).save(str(large), "PNG"):
        raise SystemExit("failed to write icon.png")

    image = Image.open(large).convert("RGBA")
    image.save(
        assets / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote", large)
    print("wrote", assets / "icon.ico")


if __name__ == "__main__":
    main()
