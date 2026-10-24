"""Reusable painted widgets: translucent cards, icon buttons, switches, chips."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import Palette, mix_hex, rgba
from .icons import icon as make_icon


# --------------------------------------------------------------------------- cards
def _rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def paint_card(painter: QPainter, rect: QRectF, radius: float, base: QColor, alpha: int,
               palette: Palette) -> None:
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = _rounded_path(rect, radius)

    top = mix_hex(base, "#FFFFFF" if palette.dark else "#FFFFFF", 0.10 if palette.dark else 0.0)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0.0, QColor(top.red(), top.green(), top.blue(), alpha))
    gradient.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), alpha))

    painter.fillPath(path, gradient)

    if palette.dark:
        border = QColor(255, 255, 255, max(14, int(alpha * 0.10)))
    else:
        border = QColor(18, 26, 40, max(14, int(alpha * 0.09)))
    painter.setPen(QPen(border, 1))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

    # gentle top highlight
    highlight = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
    if palette.dark:
        highlight.setColorAt(0.0, QColor(255, 255, 255, 0))
        highlight.setColorAt(0.5, QColor(255, 255, 255, 26))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    else:
        highlight.setColorAt(0.0, QColor(255, 255, 255, 0))
        highlight.setColorAt(0.5, QColor(255, 255, 255, 160))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
    pen = QPen(highlight, 1)
    painter.setPen(pen)
    painter.drawLine(
        QPointF(rect.left() + radius * 0.6, rect.top() + 0.6),
        QPointF(rect.right() - radius * 0.6, rect.top() + 0.6),
    )
    painter.restore()


class GlassCard(QWidget):
    """A rounded, semi-transparent surface that children can be laid out on."""

    def __init__(self, palette: Palette, radius: int = 24, opacity: int = 82,
                 base: QColor | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.palette = palette
        self.radius = radius
        self.opacity = opacity
        self.base = base if base is not None else QColor(*palette.card)
        self.accent: QColor | None = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def set_palette(self, palette: Palette) -> None:
        self.palette = palette
        self.update()

    def set_opacity(self, opacity: int) -> None:
        self.opacity = max(0, min(100, int(opacity)))
        self.update()

    def set_base(self, color: QColor) -> None:
        self.base = color
        self.update()

    def set_accent(self, color: QColor | None) -> None:
        self.accent = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        alpha = round(255 * self.opacity / 100)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        paint_card(painter, rect, self.radius, self.base, alpha, self.palette)
        if self.accent is not None and alpha > 0:
            painter.save()
            painter.setClipPath(_rounded_path(rect, self.radius))
            glow = QRadialGradient(
                QPointF(rect.right() - 20, rect.top() + 10), rect.width() * 0.85
            )
            top = QColor(self.accent)
            top.setAlpha(min(52, int(alpha * 0.22)))
            glow.setColorAt(0.0, top)
            glow.setColorAt(1.0, QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawRect(rect)
            painter.restore()


def apply_shadow(widget: QWidget, palette: Palette, blur: int = 42, y: int = 12) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, palette.shadow_alpha))
    widget.setGraphicsEffect(effect)


# -------------------------------------------------------------------------- inputs
class IconButton(QToolButton):
    def __init__(self, name: str, color: str, size: int = 18, tip: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._color = color
        self._size = size
        self.setIcon(make_icon(name, color, size))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(size + 12, size + 12)
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoRaise(True)
        if tip:
            self.setToolTip(tip)

    def set_visual(self, name: str | None = None, color: str | None = None) -> None:
        self._name = name or self._name
        self._color = color or self._color
        self.setIcon(make_icon(self._name, self._color, self._size))


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._offset = 1.0 if checked else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _on_anim(self, value) -> None:
        self._offset = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        track = QRectF(1, 2, self.width() - 2, self.height() - 4)
        on_color = QColor(self.property("accent") or "#7F9CFF")
        off_color = QColor(255, 255, 255, 30) if self.property("dark") else QColor(20, 28, 42, 28)
        if self.isChecked():
            color = QColor(on_color)
            color.setAlpha(235)
        else:
            color = off_color
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        radius = (self.height() - 8) / 2
        cx = 5 + radius + self._offset * (self.width() - 10 - radius * 2)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPointF(cx, self.height() / 2), radius, radius)


class ColorSwatch(QAbstractButton):
    def __init__(self, color: str, selected: bool = False, diameter: int = 24,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color = color
        self._selected = selected
        self.setCheckable(True)
        self.setChecked(selected)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(diameter + 6, diameter + 6)
        self._diameter = diameter
        self.toggled.connect(self._on_toggle)

    def _on_toggle(self, checked: bool) -> None:
        self._selected = checked
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        center = QRectF(self.rect()).center()
        r = self._diameter / 2
        if self._selected:
            painter.setPen(QPen(QColor(self.color), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, r + 3.5, r + 3.5)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(center, r, r)


class Separator(QFrame):
    def __init__(self, color: QColor | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color or QColor(255, 255, 255, 20)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._color)


class DragBar(QWidget):
    """Header strip that moves its top-level window when dragged."""

    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._offset: QPoint | None = None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._offset = None
        super().mouseReleaseEvent(event)


# ------------------------------------------------------------------------- helpers
def label(text: str = "", object_name: str = "", size: int | None = None,
          weight: int | None = None, color: str | None = None,
          parent: QWidget | None = None) -> QLabel:
    widget = QLabel(text, parent)
    if object_name:
        widget.setObjectName(object_name)
    font = widget.font()
    if size:
        font.setPointSizeF(size)
    if weight:
        font.setWeight(QFont.Weight(weight))
    widget.setFont(font)
    if color:
        widget.setStyleSheet(f"color: {color};")
    widget.setAttribute(Qt.WA_TranslucentBackground, True)
    return widget


def hline(palette: Palette) -> Separator:
    line = Separator()
    line.setProperty("line_color", palette.border)
    # property is a CSS string, so convert manually below
    return line


def vbox(parent: QWidget | None = None, margins: tuple[int, int, int, int] = (0, 0, 0, 0),
         spacing: int = 8) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def hbox(parent: QWidget | None = None, margins: tuple[int, int, int, int] = (0, 0, 0, 0),
         spacing: int = 8) -> QHBoxLayout:
    layout = QHBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


class SectionTitle(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("section")
        font = self.font()
        font.setPointSizeF(9.0)
        font.setWeight(QFont.DemiBold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        self.setFont(font)
