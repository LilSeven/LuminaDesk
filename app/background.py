"""Custom widget background image helpers.

The cropped image is stored inside the app data directory and referenced by
file name, so moving the original photo does not break the widget.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtGui import QImage, QImageReader, QPixmap

from .config import Config
from .paths import data_dir


BACKGROUND_PREFIX = "background-"
MAX_BACKGROUND_WIDTH = 1600


def background_path(cfg: Config) -> Path | None:
    name = (cfg.background_file or "").strip()
    if not name:
        return None
    path = data_dir() / name
    return path if path.is_file() else None


def load_background(cfg: Config) -> QPixmap | None:
    path = background_path(cfg)
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    return None if pixmap.isNull() else pixmap


def load_image(path: str | Path) -> QImage:
    """Read an image with EXIF orientation applied."""
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    return reader.read()


def save_background(image: QImage) -> str:
    """Persist a cropped image and return its file name in the data directory."""
    if image.isNull():
        raise OSError("裁切结果为空")
    if image.width() > MAX_BACKGROUND_WIDTH:
        image = image.scaledToWidth(MAX_BACKGROUND_WIDTH)
    image = image.convertToFormat(QImage.Format_RGB32)

    name = f"{BACKGROUND_PREFIX}{uuid.uuid4().hex[:12]}.png"
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if not image.save(str(folder / name), "PNG"):
        raise OSError("无法写入背景图片")
    return name
