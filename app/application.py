"""Application controller: owns the clock, note windows, dialogs and tray."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialog, QSystemTrayIcon

from .autostart import set_enabled
from .category_dialog import CategoryDialog
from .config import Config
from .dialogs import AlertDialog, ConfirmDialog
from .note_manager import NoteManager
from .notes import NoteStore
from .settings import SettingsDialog
from .theme import build_qss, palette_for
from .tray import Tray
from .ui.clock_widget import ClockWidget
from .ui.note_window import NoteWindow
from .weather import WeatherService


class LuminaApp(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.cfg = Config.load()
        self.palette = palette_for(self.cfg.theme)
        self.store = NoteStore(parent=self)
        self.weather = WeatherService(self)

        self.clock = ClockWidget(self.cfg)
        self.tray = Tray(self)
        self._windows: dict[str, NoteWindow] = {}
        self._manager: NoteManager | None = None
        self._settings: SettingsDialog | None = None
        self._has_weather = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self.cfg.save)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_weather)

        self._connect()
        self._apply_theme()

        self.clock.set_city(self.cfg.city_name)
        self.clock.set_note_count(self.store.count())
        self.clock.apply_transparency(self.cfg.transparency)
        self.clock.set_always_on_top(self.cfg.always_on_top)
        self._place_clock()

        if self.cfg.autostart:
            set_enabled(True)

        self._refresh_timer.start(max(1, self.cfg.refresh_minutes) * 60_000)
        self.clock.show()
        self.tray.show()
        self.refresh_weather()

        QTimer.singleShot(280, self._restore_notes)

    # ------------------------------------------------------------------ wiring
    def _connect(self) -> None:
        self.clock.settings_requested.connect(self.open_settings)
        self.clock.city_requested.connect(self.open_settings)
        self.clock.notes_requested.connect(self.open_manager)
        self.clock.new_note_requested.connect(self.new_note)
        self.clock.refresh_requested.connect(self.refresh_weather)
        self.clock.quit_requested.connect(self.quit)
        self.clock.geometry_saved.connect(self._on_geometry_saved)
        self.clock.transparency_adjusted.connect(self._on_transparency)

        self.weather.updated.connect(self._on_weather)
        self.weather.failed.connect(self._on_weather_failed)

        self.store.changed.connect(self._on_store_changed)

        self.tray.show_requested.connect(self.show_clock)
        self.tray.new_note_requested.connect(self.new_note)
        self.tray.notes_requested.connect(self.open_manager)
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.quit_requested.connect(self.quit)

    # ------------------------------------------------------------------ theme
    def _apply_theme(self) -> None:
        self.palette = palette_for(self.cfg.theme)
        self.app.setStyleSheet(build_qss(self.palette, self.cfg.accent))
        self.clock.apply_theme(self.palette, self.cfg.accent)
        for window in self._windows.values():
            window.refresh_theme(self.palette)

    def _place_clock(self) -> None:
        self.clock.adjustSize()
        screen = self.app.primaryScreen()
        if self.cfg.window_x >= 0 and self.cfg.window_y >= 0:
            self.clock.move(self.cfg.window_x, self.cfg.window_y)
            return
        if screen is None:
            return
        area = screen.availableGeometry()
        x = area.right() - self.clock.width() - 18
        y = area.top() + 20
        self.clock.move(max(area.left(), x), max(area.top(), y))

    # ------------------------------------------------------------------ weather
    def refresh_weather(self) -> None:
        cached = self.weather.load_cache(self.cfg.city_name)
        if cached is not None:
            self._has_weather = True
            self.clock.set_weather(cached, cached=True)
        elif not self._has_weather:
            self.clock.set_loading()
        self.weather.refresh(self.cfg.city_name, self.cfg.latitude, self.cfg.longitude)

    def _on_weather(self, weather) -> None:
        self._has_weather = True
        self.clock.set_weather(weather, cached=False)
        self.tray.set_tooltip(
            f"{weather.city} · {weather.temp:.0f}°C {weather.description} · Lumina Desk"
        )

    def _on_weather_failed(self, message: str) -> None:
        if not self._has_weather:
            self.clock.set_weather_error(message)

    # ------------------------------------------------------------------ notes
    def _restore_notes(self) -> None:
        for note in list(self.store.notes):
            if note.open_window:
                self.open_note(note.id, animate=False)

    def open_note(self, note_id: str, animate: bool = True) -> None:
        note = self.store.get(note_id)
        if note is None:
            return
        window = self._windows.get(note_id)
        if window is None:
            window = NoteWindow(self.store, note, self.palette)
            window.delete_requested.connect(self.delete_note)
            window.categories_requested.connect(lambda: self.open_categories(window))
            window.new_note_requested.connect(lambda: self.new_note(note.category_id))
            self._windows[note_id] = window
        window.refresh_theme(self.palette)
        window.show_note()
        if animate:
            window.raise_()
            window.activateWindow()

    def new_note(self, category_id: str = "") -> None:
        note = self.store.create_note(category_id or None)
        if self.clock.isVisible():
            base = self.clock.geometry()
            offset = (len(self._windows) % 6) * 26
            note.x = max(20, base.x() - 300)
            note.y = max(20, base.y() + 46 + offset)
        self.store.save()
        self.open_note(note.id)

    def delete_note(self, note_id: str) -> None:
        note = self.store.get(note_id)
        if note is None:
            return
        title = note.title.strip() or note.preview(24) or "无标题便签"
        if not ConfirmDialog.ask(
            self.clock, self.palette, "删除便签",
            f"确定删除「{title}」吗？\n删除后无法恢复。",
            "删除", danger=True,
        ):
            return
        window = self._windows.pop(note_id, None)
        if window is not None:
            window.hide_note()
            window.deleteLater()
        self.store.remove_note(note_id)

    def _on_store_changed(self) -> None:
        self.clock.set_note_count(self.store.count())
        for window in self._windows.values():
            window.refresh_category()

    def open_manager(self) -> None:
        if self._manager is not None:
            self._manager.show()
            self._manager.raise_()
            self._manager.activateWindow()
            return
        self._manager = NoteManager(self.clock, self.palette, self.store)
        self._manager.setModal(False)
        self._manager.setWindowModality(Qt.NonModal)
        self._manager.setAttribute(Qt.WA_DeleteOnClose, True)
        self._manager.open_requested.connect(self.open_note)
        self._manager.delete_requested.connect(self.delete_note)
        self._manager.new_note_requested.connect(self.new_note)
        self._manager.categories_requested.connect(lambda: self.open_categories(self._manager))
        self._manager.destroyed.connect(self._manager_gone)
        self._manager.show()
        self._manager.raise_()
        self._manager.activateWindow()

    def _manager_gone(self) -> None:
        self._manager = None

    # ------------------------------------------------------------------ dialogs
    def open_categories(self, parent=None) -> None:
        dialog = CategoryDialog(parent or self.clock, self.palette, self.store)
        dialog.exec()
        self._on_store_changed()

    def open_settings(self) -> None:
        snapshot = replace(self.cfg)
        dialog = SettingsDialog(self.clock, self.palette, self.cfg)
        self._settings = dialog
        dialog.changed.connect(self._apply_live_settings)
        dialog.categories_requested.connect(lambda: self.open_categories(dialog))
        result = dialog.exec()
        self._settings = None
        if result == QDialog.Accepted:
            self._apply_live_settings()
            self.cfg.save()
            self._refresh_timer.start(max(1, self.cfg.refresh_minutes) * 60_000)
            if self.cfg.autostart != snapshot.autostart:
                if not set_enabled(self.cfg.autostart):
                    AlertDialog.show_message(
                        self.clock, self.palette, "无法修改开机启动",
                        "写入注册表启动项失败。程序仍可正常使用，请手动将 Lumina Desk 加入启动项。",
                    )
                    self.cfg.autostart = snapshot.autostart
            if (self.cfg.city_name, self.cfg.latitude, self.cfg.longitude) != (
                snapshot.city_name, snapshot.latitude, snapshot.longitude
            ):
                self.refresh_weather()
        else:
            for name in self.cfg.__dataclass_fields__:
                setattr(self.cfg, name, getattr(snapshot, name))
            self._apply_live_settings()

    def _apply_live_settings(self) -> None:
        self._apply_theme()
        self.clock.apply_transparency(self.cfg.transparency)
        self.clock.set_always_on_top(self.cfg.always_on_top)
        self.clock.set_city(self.cfg.city_name)
        self.clock._tick()
        self._save_timer.start()

    # ------------------------------------------------------------------ misc
    def _on_geometry_saved(self, x: int, y: int) -> None:
        self.cfg.window_x = int(x)
        self.cfg.window_y = int(y)
        self._save_timer.start()

    def _on_transparency(self, value: int) -> None:
        self.cfg.transparency = int(value)
        self._save_timer.start()

    def show_clock(self) -> None:
        self.clock.show()
        self.clock.raise_()
        self.clock.activateWindow()

    def quit(self) -> None:
        for window in list(self._windows.values()):
            window._flush()
            # Hide rather than close: closeEvent is vetoed by the note window,
            # and an open tool window can keep QApplication.quit() from leaving
            # the event loop. open_window stays True so it reopens next launch.
            window.hide()
        self.store.save()
        self._save_timer.stop()
        self._refresh_timer.stop()
        self.cfg.save()
        self.clock.hide()
        self.tray.hide()
        self.app.quit()
        QTimer.singleShot(300, lambda: self.app.exit(0))
