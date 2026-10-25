"""Visual smoke test for custom background + crop dialog."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("LUMINA_DATA_DIR", os.path.join(tempfile.gettempdir(), "lumina-bg-test"))

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from app.background import save_background
from app.config import Config
from app.image_crop import BackgroundCropDialog
from app.paths import data_dir
from app.settings import SettingsDialog
from app.theme import build_qss, palette_for
from app.ui.clock_widget import ClockWidget


def make_photo(width: int = 1600, height: int = 900) -> QImage:
    image = QImage(width, height, QImage.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    sky = QLinearGradient(0, 0, 0, height)
    sky.setColorAt(0.0, QColor("#24345C"))
    sky.setColorAt(0.48, QColor("#9B6B8E"))
    sky.setColorAt(0.72, QColor("#E39A78"))
    sky.setColorAt(1.0, QColor("#F2C89B"))
    painter.fillRect(image.rect(), sky)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 238, 210, 220))
    painter.drawEllipse(QPointF(width * 0.72, height * 0.36), 110, 110)

    painter.setBrush(QColor("#1C2238"))
    painter.drawEllipse(QPointF(width * 0.14, height * 1.06), 520, 380)
    painter.setBrush(QColor("#232A44"))
    painter.drawEllipse(QPointF(width * 0.62, height * 1.12), 620, 420)
    painter.setBrush(QColor("#2D3552"))
    painter.drawEllipse(QPointF(width * 0.96, height * 1.04), 460, 350)

    painter.setPen(QColor(255, 240, 220, 80))
    for i in range(7):
        y = height * (0.52 + i * 0.035)
        painter.drawLine(QPointF(0, y), QPointF(width, y))
    painter.end()
    return image


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    palette = palette_for("dark")
    app.setStyleSheet(build_qss(palette, "#7F9CFF"))

    cfg = Config()
    clock = ClockWidget(cfg)
    clock.apply_theme(palette, "#7F9CFF")
    clock.show()

    photo = make_photo()
    crop = BackgroundCropDialog(clock, palette, photo, clock.background_ratio())
    crop.show()

    def capture_crop() -> None:
        print("capture crop", flush=True)
        crop.grab().save("shots/crop-dialog.png")
        # Pick a deliberately off-center crop to verify the mapping.
        dialog_crop = crop.canvas.crop
        dialog_crop.translate(-photo.width() * 0.08, -photo.height() * 0.04)
        crop.canvas.crop = crop.canvas._clamp_move(dialog_crop)
        crop.canvas.update()
        QTimer.singleShot(250, capture_crop_moved)

    def capture_crop_moved() -> None:
        print("capture moved", flush=True)
        crop.grab().save("shots/crop-dialog-moved.png")
        cropped = crop.canvas.result_image()
        print("cropped", cropped.width(), cropped.height(), flush=True)
        name = save_background(cropped)
        print("saved", name, flush=True)
        cfg.background_file = name
        clock.set_background(QPixmap(str(data_dir() / name)))
        print("background set", flush=True)
        crop.close()
        QTimer.singleShot(350, capture_clock)

    def capture_clock() -> None:
        print("capture clock", flush=True)
        clock.grab().save("shots/clock-background.png")
        settings = SettingsDialog(clock, palette, cfg, background_ratio=clock.background_ratio())
        settings.show()
        QTimer.singleShot(350, lambda: capture_settings(settings))

    def capture_settings(settings: SettingsDialog) -> None:
        print("capture settings", flush=True)
        settings.grab().save("shots/settings-background.png")
        settings.close()
        clock.close()
        app.quit()

    QTimer.singleShot(500, capture_crop)
    QTimer.singleShot(6000, lambda: app.exit(2))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
