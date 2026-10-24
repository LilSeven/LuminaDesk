"""Lumina Desk entry point."""
from __future__ import annotations

import multiprocessing
import os
import sys
import traceback
from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.application import LuminaApp
from app.paths import APP_DISPLAY_NAME, APP_NAME, VERSION, data_dir
from app.single_instance import SingleInstance
from app.ui.icons import app_icon


def _write_crash_log(text: str) -> None:
    try:
        folder = data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "app.log"
        if path.exists() and path.stat().st_size > 1_000_000:
            tail = path.read_text(encoding="utf-8", errors="replace")[-200_000:]
            path.write_text(tail, encoding="utf-8")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{text}\n")
    except OSError:
        pass


def _excepthook(exc_type, exc, tb) -> None:
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    _write_crash_log(text)
    sys.stderr.write(text)


def main() -> int:
    multiprocessing.freeze_support()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setOrganizationName("LilSeven")
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    sys.excepthook = _excepthook

    guard = SingleInstance(f"{APP_NAME}-{VERSION}")
    if not guard.acquire():
        return 0

    try:
        controller = LuminaApp(app)
    except Exception as exc:  # noqa: BLE001 - surface startup failures to the user
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        _write_crash_log(text)
        QMessageBox.critical(
            None, f"{APP_DISPLAY_NAME} 启动失败",
            f"程序启动时遇到错误：\n\n{exc}\n\n日志已写入：{data_dir() / 'app.log'}",
        )
        return 1

    guard.activated.connect(controller.show_clock)

    # Headless smoke check used by packaging/CI: start normally, then quit.
    smoke_exit = os.environ.get("LUMINA_SMOKE_EXIT")
    if smoke_exit:
        try:
            QTimer.singleShot(int(float(smoke_exit) * 1000), controller.quit)
        except ValueError:
            pass
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
