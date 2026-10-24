"""Frameless translucent dialogs used across the app."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .theme import Palette
from .ui.icons import icon as make_icon
from .ui.widgets import DragBar, GlassCard, IconButton, apply_shadow, label, vbox


class GlassDialog(QDialog):
    """Rounded dialog with a draggable header and a translucent card."""

    def __init__(self, parent: QWidget | None, palette: Palette, title: str,
                 width: int = 420, subtitle: str = "") -> None:
        super().__init__(parent)
        self.palette = palette
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setFixedWidth(width)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.setSpacing(0)

        self.card = GlassCard(palette, radius=22, opacity=97, base=QColor(*palette.dialog))
        self.card.set_accent(QColor("#7F9CFF"))
        apply_shadow(self.card, palette, blur=44, y=14)
        outer.addWidget(self.card)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(22, 16, 22, 18)
        self.card_layout.setSpacing(12)

        self.header = DragBar(self, self.card)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(1)
        self.title_label = label(title, "dialogTitle")
        titles.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = label(subtitle, "faint")
            titles.addWidget(self.subtitle_label)
        header_layout.addLayout(titles, 1)

        self.close_btn = IconButton("close", palette.sub, 14, "关闭", self.header)
        self.close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self.close_btn, 0, Qt.AlignTop)
        self.card_layout.addWidget(self.header)

        self.body = QWidget(self.card)
        self.body.setObjectName("transparent")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(12)
        self.card_layout.addWidget(self.body)

        self.footer = QWidget(self.card)
        self.footer.setObjectName("transparent")
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(0, 2, 0, 0)
        self.footer_layout.setSpacing(8)
        self.footer_layout.addStretch(1)
        self.card_layout.addWidget(self.footer)

    def add_widget(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.body_layout.addLayout(layout)

    def add_button(self, text: str, object_name: str = "", slot=None) -> QPushButton:
        button = QPushButton(text, self.footer)
        if object_name:
            button.setObjectName(object_name)
        button.setCursor(Qt.PointingHandCursor)
        if slot is not None:
            button.clicked.connect(slot)
        self.footer_layout.addWidget(button)
        return button

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.adjustSize()
        screen = None
        if self.parentWidget() is not None:
            screen = QApplication.screenAt(self.parentWidget().geometry().center())
        screen = screen or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(
                area.center().x() - self.width() // 2,
                area.center().y() - self.height() // 2,
            )


class ConfirmDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette, title: str,
                 message: str, confirm_text: str = "确认", danger: bool = False,
                 cancel_text: str = "取消") -> None:
        super().__init__(parent, palette, title, width=390)
        self.confirmed = False

        self.message = QLabel(message, self.body)
        self.message.setObjectName("sub")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.add_widget(self.message)

        self.add_button(cancel_text, "ghost", self.reject)
        self.add_button(confirm_text, "danger" if danger else "accent", self._accept)

    def _accept(self) -> None:
        self.confirmed = True
        self.accept()

    @classmethod
    def ask(cls, parent: QWidget | None, palette: Palette, title: str, message: str,
            confirm_text: str = "确认", danger: bool = False) -> bool:
        dialog = cls(parent, palette, title, message, confirm_text, danger)
        dialog.exec()
        return dialog.confirmed


class AlertDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette, title: str,
                 message: str) -> None:
        super().__init__(parent, palette, title, width=400)
        text = QLabel(message, self.body)
        text.setObjectName("sub")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.add_widget(text)
        self.add_button("知道了", "accent", self.accept)

    @classmethod
    def show_message(cls, parent: QWidget | None, palette: Palette, title: str,
                     message: str) -> None:
        cls(parent, palette, title, message).exec()
