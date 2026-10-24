"""Hand-drawn vector icons (no image assets, crisp at every DPI)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

ICON_COLOR = "#F3F5F9"


def _pen(color: str | QColor, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _cloud_path(cx: float, cy: float, s: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(cx - 9 * s, cy + 3 * s), 9.5 * s, 9.5 * s)
    path.addEllipse(QPointF(cx + 2 * s, cy - 3 * s), 12.5 * s, 12.5 * s)
    path.addEllipse(QPointF(cx + 14 * s, cy + 3 * s), 8.5 * s, 8.5 * s)
    body = QPainterPath()
    body.addRoundedRect(QRectF(cx - 19 * s, cy + 3 * s, 39 * s, 12 * s), 6 * s, 6 * s)
    merged = path.united(body)
    merged.setFillRule(Qt.WindingFill)
    return merged


def paint_icon(painter: QPainter, rect: QRectF, name: str, color: str | QColor,
               width: float = 1.8) -> None:
    """Draw a 24x24 designed icon into ``rect``."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    scale = rect.width() / 24.0
    painter.translate(rect.topLeft())
    painter.scale(scale, scale)
    painter.setPen(_pen(color, width))
    painter.setBrush(Qt.NoBrush)

    if name == "plus":
        painter.drawLine(QPointF(12, 5.5), QPointF(12, 18.5))
        painter.drawLine(QPointF(5.5, 12), QPointF(18.5, 12))
    elif name == "minus":
        painter.drawLine(QPointF(5.5, 12), QPointF(18.5, 12))
    elif name == "close":
        painter.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
        painter.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))
    elif name == "gear":
        teeth = 8
        path = QPainterPath()
        outer, inner = 8.6, 6.5
        for i in range(teeth * 2):
            angle = math.pi * i / teeth - math.pi / 2
            radius = outer if i % 2 == 0 else inner
            point = QPointF(12 + radius * math.cos(angle), 12 + radius * math.sin(angle))
            if i == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        hole = QPainterPath()
        hole.addEllipse(QPointF(12, 12), 3.0, 3.0)
        path.setFillRule(Qt.OddEvenFill)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
        painter.setBrush(QColor(0, 0, 0, 0))
    elif name == "pin":
        path = QPainterPath()
        path.moveTo(7.2, 4.4)
        path.lineTo(16.8, 4.4)
        path.lineTo(16.8, 19.2)
        path.lineTo(12.0, 15.2)
        path.lineTo(7.2, 19.2)
        path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif name == "pin_off":
        path = QPainterPath()
        path.moveTo(7.2, 4.4)
        path.lineTo(16.8, 4.4)
        path.lineTo(16.8, 19.2)
        path.lineTo(12.0, 15.2)
        path.lineTo(7.2, 19.2)
        path.closeSubpath()
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.drawLine(QPointF(4.6, 19.4), QPointF(19.4, 4.6))
    elif name == "list":
        for i, y in enumerate((7.0, 12.0, 17.0)):
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(5.6, y), 1.15, 1.15)
            painter.setPen(_pen(color, 1.8))
            painter.drawLine(QPointF(9.2, y), QPointF(19.0, y))
    elif name == "refresh":
        rect_arc = QRectF(5.0, 5.0, 14.0, 14.0)
        painter.drawArc(rect_arc, 40 * 16, 290 * 16)
        arrow = QPainterPath()
        arrow.moveTo(17.6, 3.6)
        arrow.lineTo(19.4, 8.4)
        arrow.lineTo(14.5, 7.6)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(arrow)
    elif name == "chevron_down":
        painter.drawLine(QPointF(7.0, 9.8), QPointF(12.0, 14.8))
        painter.drawLine(QPointF(12.0, 14.8), QPointF(17.0, 9.8))
    elif name == "chevron_right":
        painter.drawLine(QPointF(9.8, 6.5), QPointF(14.8, 12.0))
        painter.drawLine(QPointF(14.8, 12.0), QPointF(9.8, 17.5))
    elif name == "trash":
        painter.drawLine(QPointF(4.5, 6.5), QPointF(19.5, 6.5))
        painter.drawLine(QPointF(9.5, 6.5), QPointF(9.8, 3.8))
        painter.drawLine(QPointF(9.8, 3.8), QPointF(14.2, 3.8))
        painter.drawLine(QPointF(14.2, 3.8), QPointF(14.5, 6.5))
        path = QPainterPath()
        path.moveTo(6.8, 6.8)
        path.lineTo(17.2, 6.8)
        path.lineTo(16.2, 20.0)
        path.lineTo(7.8, 20.0)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(10.4, 10.2), QPointF(10.7, 16.8))
        painter.drawLine(QPointF(13.6, 10.2), QPointF(13.3, 16.8))
    elif name == "check":
        painter.drawLine(QPointF(5.2, 12.2), QPointF(9.8, 17.0))
        painter.drawLine(QPointF(9.8, 17.0), QPointF(18.8, 6.8))
    elif name == "search":
        painter.drawEllipse(QPointF(10.8, 10.8), 6.0, 6.0)
        painter.drawLine(QPointF(15.3, 15.3), QPointF(19.8, 19.8))
    elif name == "note":
        path = QPainterPath()
        path.addRoundedRect(QRectF(4.8, 3.8, 14.4, 16.4), 3.2, 3.2)
        painter.drawPath(path)
        painter.drawLine(QPointF(8.2, 9.0), QPointF(15.8, 9.0))
        painter.drawLine(QPointF(8.2, 12.6), QPointF(15.8, 12.6))
        painter.drawLine(QPointF(8.2, 16.2), QPointF(13.0, 16.2))
    elif name == "more":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        for x in (7.0, 12.0, 17.0):
            painter.drawEllipse(QPointF(x, 12.0), 1.35, 1.35)
    elif name == "moon":
        outer = QPainterPath()
        outer.addEllipse(QPointF(12, 12), 7.6, 7.6)
        inner = QPainterPath()
        inner.addEllipse(QPointF(15.2, 8.6), 6.6, 6.6)
        crescent = outer.subtracted(inner)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(crescent)
    elif name == "sun":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(12, 12), 3.8, 3.8)
        painter.setPen(_pen(color, 1.7))
        for i in range(8):
            angle = math.pi * i / 4
            painter.drawLine(
                QPointF(12 + 6.4 * math.cos(angle), 12 + 6.4 * math.sin(angle)),
                QPointF(12 + 8.8 * math.cos(angle), 12 + 8.8 * math.sin(angle)),
            )
    elif name == "clock":
        painter.drawEllipse(QPointF(12, 12), 8.4, 8.4)
        painter.drawLine(QPointF(12, 12), QPointF(12, 7.2))
        painter.drawLine(QPointF(12, 12), QPointF(16.0, 13.6))
    elif name == "search_note":
        painter.drawEllipse(QPointF(10.5, 10.5), 5.6, 5.6)
        painter.drawLine(QPointF(14.8, 14.8), QPointF(19.2, 19.2))
    elif name == "edit":
        path = QPainterPath()
        path.moveTo(5.0, 19.0)
        path.lineTo(6.2, 14.4)
        path.lineTo(15.6, 5.0)
        path.lineTo(19.0, 8.4)
        path.lineTo(9.6, 17.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(13.4, 7.2), QPointF(16.8, 10.6))
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(3.5, 7.0)
        path.lineTo(9.5, 7.0)
        path.lineTo(11.2, 9.0)
        path.lineTo(20.5, 9.0)
        path.lineTo(20.5, 18.8)
        path.lineTo(3.5, 18.8)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "external":
        painter.drawLine(QPointF(13.5, 5.0), QPointF(19.0, 5.0))
        painter.drawLine(QPointF(19.0, 5.0), QPointF(19.0, 10.5))
        painter.drawLine(QPointF(19.0, 5.0), QPointF(11.5, 12.5))
        path = QPainterPath()
        path.moveTo(17.0, 14.0)
        path.lineTo(17.0, 19.0)
        path.lineTo(5.0, 19.0)
        path.lineTo(5.0, 7.0)
        path.lineTo(10.0, 7.0)
        painter.drawPath(path)
    elif name == "drag":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        for y in (8.0, 12.0, 16.0):
            for x in (10.0, 14.0):
                painter.drawEllipse(QPointF(x, y), 1.1, 1.1)
    elif name == "palette":
        painter.drawEllipse(QPointF(12, 12), 8.4, 8.4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        for x, y in ((8.6, 10.0), (12.0, 8.4), (15.4, 10.0)):
            painter.drawEllipse(QPointF(x, y), 1.15, 1.15)
    elif name == "globe":
        painter.drawEllipse(QPointF(12, 12), 8.4, 8.4)
        painter.drawEllipse(QPointF(12, 12), 3.8, 8.4)
        painter.drawLine(QPointF(3.8, 12), QPointF(20.2, 12))
    else:
        painter.drawEllipse(QPointF(12, 12), 7.0, 7.0)

    painter.restore()


def pixmap(name: str, color: str | QColor, size: int = 18) -> QPixmap:
    dpr = 2.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    paint_icon(painter, QRectF(0, 0, size, size), name, color)
    painter.end()
    return pm


def icon(name: str, color: str | QColor, size: int = 18) -> QIcon:
    return QIcon(pixmap(name, color, size))


def dot_icon(color: str | QColor, size: int = 10) -> QIcon:
    dpr = 2.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    painter.end()
    return QIcon(pm)


def _cloud_pixmap(painter: QPainter, kind: str, dark: bool = True) -> None:
    """Weather illustration on a 64x64 canvas, bottom-left origin at 0,0."""
    sun = QColor("#FFC96B")
    moon = QColor("#D7E2FF") if dark else QColor("#7C8FD6")
    cloud_hi = QColor("#DEE7F4") if dark else QColor("#D5DFEE")
    cloud_lo = QColor("#AEBED6") if dark else QColor("#8FA4C2")
    rain = QColor("#7FB8FF") if dark else QColor("#4E90E8")
    bolt = QColor("#FFD166") if dark else QColor("#F0A93B")
    snow = QColor("#E8F1FF") if dark else QColor("#6E9FD6")

    painter.setRenderHint(QPainter.Antialiasing, True)

    def draw_sun(cx: float, cy: float, r: float) -> None:
        painter.setPen(Qt.NoPen)
        painter.setBrush(sun)
        painter.drawEllipse(QPointF(cx, cy), r, r)
        pen = _pen(sun, 2.4)
        painter.setPen(pen)
        for i in range(8):
            angle = math.pi * i / 4
            painter.drawLine(
                QPointF(cx + (r + 3.2) * math.cos(angle), cy + (r + 3.2) * math.sin(angle)),
                QPointF(cx + (r + 7.0) * math.cos(angle), cy + (r + 7.0) * math.sin(angle)),
            )

    def draw_cloud(cx: float, cy: float, s: float, gradient: bool = True) -> None:
        if gradient:
            grad = QLinearGradient(0, cy - 12 * s, 0, cy + 16 * s)
            grad.setColorAt(0.0, cloud_hi)
            grad.setColorAt(1.0, cloud_lo)
            painter.setBrush(grad)
        else:
            painter.setBrush(cloud_hi)
        painter.setPen(Qt.NoPen)
        # Draw overlapping primitives with the same brush instead of a boolean
        # union: united() can leave interior sub-paths that render as holes.
        painter.drawEllipse(QPointF(cx - 9 * s, cy + 3 * s), 9.5 * s, 9.5 * s)
        painter.drawEllipse(QPointF(cx + 2 * s, cy - 3 * s), 12.5 * s, 12.5 * s)
        painter.drawEllipse(QPointF(cx + 14 * s, cy + 3 * s), 8.5 * s, 8.5 * s)
        painter.drawRoundedRect(
            QRectF(cx - 19 * s, cy + 3 * s, 39 * s, 12 * s), 6 * s, 6 * s
        )

    if kind == "sun":
        draw_sun(32, 32, 10.5)
    elif kind == "moon":
        outer = QPainterPath()
        outer.addEllipse(QPointF(33, 32), 13.0, 13.0)
        inner = QPainterPath()
        inner.addEllipse(QPointF(42, 26), 11.5, 11.5)
        painter.setBrush(moon)
        painter.setPen(Qt.NoPen)
        painter.drawPath(outer.subtracted(inner))
        painter.setPen(_pen(moon, 2.0))
        for x, y, r in ((19, 18, 1.6), (17, 38, 1.1), (47, 47, 1.4)):
            painter.setBrush(moon)
            painter.drawEllipse(QPointF(x, y), r, r)
    elif kind == "cloud-sun":
        draw_sun(22, 21, 7.5)
        draw_cloud(34, 34, 1.02)
    elif kind == "cloud-moon":
        outer = QPainterPath()
        outer.addEllipse(QPointF(23, 19), 8.5, 8.5)
        inner = QPainterPath()
        inner.addEllipse(QPointF(29, 14), 7.8, 7.8)
        painter.setBrush(moon)
        painter.setPen(Qt.NoPen)
        painter.drawPath(outer.subtracted(inner))
        draw_cloud(34, 35, 1.0)
    elif kind == "cloud":
        draw_cloud(32, 31, 1.08)
    elif kind == "fog":
        draw_cloud(32, 28, 0.98)
        painter.setPen(_pen(QColor("#C4CFE0"), 3.0))
        for i, y in enumerate((48, 53, 58)):
            painter.drawLine(QPointF(18 + i * 3, y), QPointF(46 - i * 3, y))
    elif kind in ("rain", "drizzle", "sleet", "snow", "thunder"):
        draw_cloud(32, 28, 1.0)
        if kind == "rain":
            painter.setPen(_pen(rain, 3.0))
            for x in (23, 32, 41):
                painter.drawLine(QPointF(x, 47), QPointF(x - 4, 56))
        elif kind == "drizzle":
            painter.setPen(Qt.NoPen)
            painter.setBrush(rain)
            for x, y in ((23, 51), (32, 49), (41, 51)):
                painter.drawEllipse(QPointF(x, y), 1.8, 1.8)
        elif kind == "sleet":
            painter.setPen(_pen(rain, 2.6))
            painter.drawLine(QPointF(24, 47), QPointF(21, 56))
            _snowflake(painter, 39, 52, 4.2, snow)
        elif kind == "snow":
            for x in (23, 32, 41):
                _snowflake(painter, x, 52, 4.2, snow)
        elif kind == "thunder":
            path = QPainterPath()
            path.moveTo(35, 43)
            path.lineTo(26, 54)
            path.lineTo(32, 54)
            path.lineTo(28, 62)
            path.lineTo(40, 50)
            path.lineTo(34, 50)
            path.closeSubpath()
            painter.setBrush(bolt)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)
    else:
        draw_cloud(32, 31, 1.05)


def _snowflake(painter: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    painter.setPen(_pen(color, 1.8))
    for i in range(3):
        angle = math.pi * i / 3
        dx, dy = r * math.cos(angle), r * math.sin(angle)
        painter.drawLine(QPointF(cx - dx, cy - dy), QPointF(cx + dx, cy + dy))


def weather_pixmap(kind: str, size: int = 56, dark: bool = True) -> QPixmap:
    dpr = 2.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.scale(size / 64.0, size / 64.0)
    _cloud_pixmap(painter, kind, dark)
    painter.end()
    return pm


def app_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    scale = size / 256.0
    painter.scale(scale, scale)

    bg = QLinearGradient(0, 0, 256, 256)
    bg.setColorAt(0.0, QColor("#2A3350"))
    bg.setColorAt(0.55, QColor("#171C29"))
    bg.setColorAt(1.0, QColor("#10131C"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(6, 6, 244, 244), 58, 58)
    painter.setPen(QPen(QColor(255, 255, 255, 38), 2))
    painter.setBrush(bg)
    painter.drawPath(path)

    glow = QRadialGradient(128, 120, 110)
    glow.setColorAt(0.0, QColor(127, 156, 255, 90))
    glow.setColorAt(1.0, QColor(127, 156, 255, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QPointF(128, 120), 110, 110)

    ring = QLinearGradient(60, 60, 196, 196)
    ring.setColorAt(0.0, QColor("#9DB4FF"))
    ring.setColorAt(1.0, QColor("#6C7CF5"))
    pen = QPen(ring, 14)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(64, 64, 128, 128), 35 * 16, 290 * 16)

    hand_pen = QPen(QColor("#F5F7FF"), 11)
    hand_pen.setCapStyle(Qt.RoundCap)
    painter.setPen(hand_pen)
    painter.drawLine(QPointF(128, 128), QPointF(128, 88))
    painter.drawLine(QPointF(128, 128), QPointF(160, 143))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#FFC96B"))
    painter.drawEllipse(QPointF(128, 128), 8, 8)
    painter.end()
    return pm


def app_icon() -> QIcon:
    icon_obj = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon_obj.addPixmap(app_pixmap(size))
    return icon_obj
