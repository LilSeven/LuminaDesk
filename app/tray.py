"""System tray integration."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .paths import APP_DISPLAY_NAME, VERSION
from .ui.icons import app_icon


class Tray(QObject):
    show_requested = Signal()
    new_note_requested = Signal()
    notes_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self.icon = QSystemTrayIcon(app_icon(), self)
        self.icon.setToolTip(f"{APP_DISPLAY_NAME} {VERSION}")

        self.menu = QMenu()
        show_action = QAction("显示桌面挂件", self.menu)
        show_action.triggered.connect(self.show_requested.emit)
        self.menu.addAction(show_action)
        self.menu.addSeparator()

        new_action = QAction("新建便签", self.menu)
        new_action.triggered.connect(self.new_note_requested.emit)
        self.menu.addAction(new_action)

        notes_action = QAction("便签管理…", self.menu)
        notes_action.triggered.connect(self.notes_requested.emit)
        self.menu.addAction(notes_action)
        self.menu.addSeparator()

        settings_action = QAction("设置…", self.menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(settings_action)
        self.menu.addSeparator()

        quit_action = QAction("退出 Lumina Desk", self.menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(quit_action)

        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)

    def show(self) -> None:
        if self.available:
            self.icon.show()

    def hide(self) -> None:
        self.icon.hide()

    def set_tooltip(self, text: str) -> None:
        self.icon.setToolTip(text)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_requested.emit()
