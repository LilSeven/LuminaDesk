"""Interactive crop dialog for non-matching background photos."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .dialogs import GlassDialog
from .theme import Palette
from .ui.widgets import label


class CropCanvas(QWidget):
    """Photo preview with a draggable, corner-resizable crop rectangle.

    The crop rectangle is always locked to the card's aspect ratio, so the
    result never stretches. All public geometry is stored in image pixels.
    """

    HANDLE = 12.0

    def __init__(self, image: QImage, aspect: float, accent: str = "#7F9CFF",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image = image
        self.aspect = max(0.2, float(aspect))
        self.accent = QColor(accent)
        self.crop = QRectF()
        self._mode: str | None = None
        self._start_crop = QRectF()
        self._start_pos = QPointF()
        self._anchor = QPointF()
        self.setMouseTracking(True)
        self.setMinimumSize(QSize(320, 240))
        self.reset_crop()

    # ------------------------------------------------------------------ geometry
    def image_rect(self) -> QRectF:
        area = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        if self.image.isNull() or area.width() <= 0 or area.height() <= 0:
            return QRectF()
        scale = min(area.width() / self.image.width(), area.height() / self.image.height())
        width = self.image.width() * scale
        height = self.image.height() * scale
        return QRectF(
            area.center().x() - width / 2,
            area.center().y() - height / 2,
            width,
            height,
        )

    def scale(self) -> float:
        shown = self.image_rect()
        if shown.width() <= 0 or self.image.isNull():
            return 1.0
        return shown.width() / self.image.width()

    def to_widget(self, rect: QRectF) -> QRectF:
        shown = self.image_rect()
        factor = self.scale()
        return QRectF(
            shown.left() + rect.left() * factor,
            shown.top() + rect.top() * factor,
            rect.width() * factor,
            rect.height() * factor,
        )

    def to_image(self, point: QPointF) -> QPointF:
        shown = self.image_rect()
        factor = self.scale()
        return QPointF(
            (point.x() - shown.left()) / factor,
            (point.y() - shown.top()) / factor,
        )

    def reset_crop(self) -> None:
        if self.image.isNull():
            return
        width = float(self.image.width())
        height = float(self.image.height())
        if width / height > self.aspect:
            crop_h = height * 0.86
            crop_w = crop_h * self.aspect
        else:
            crop_w = width * 0.86
            crop_h = crop_w / self.aspect
        self.crop = QRectF(
            (width - crop_w) / 2,
            (height - crop_h) / 2,
            crop_w,
            crop_h,
        )
        self.update()

    def result_image(self) -> QImage:
        if self.image.isNull():
            return QImage()
        rect = self.crop.toRect().intersected(self.image.rect())
        if rect.width() < 2 or rect.height() < 2:
            return QImage()
        return self.image.copy(rect)

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#0B0D12"))

        shown = self.image_rect()
        if not self.image.isNull():
            painter.drawImage(shown, self.image)

        crop = self.to_widget(self.crop)
        outside = QPainterPath()
        outside.addRect(QRectF(self.rect()))
        hole = QPainterPath()
        hole.addRect(crop)
        painter.fillPath(outside.subtracted(hole), QColor(4, 6, 10, 150))

        # rule of thirds, then the frame and handles
        painter.save()
        painter.setClipRect(crop)
        thirds = QPen(QColor(255, 255, 255, 55), 1)
        painter.setPen(thirds)
        for i in (1, 2):
            x = crop.left() + crop.width() * i / 3
            y = crop.top() + crop.height() * i / 3
            painter.drawLine(QPointF(x, crop.top()), QPointF(x, crop.bottom()))
            painter.drawLine(QPointF(crop.left(), y), QPointF(crop.right(), y))
        painter.restore()

        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(crop.adjusted(1, 1, -1, -1), 3, 3)

        painter.setPen(QPen(self.accent, 1))
        painter.setBrush(QColor("#FFFFFF"))
        for corner in (
            crop.topLeft(), crop.topRight(), crop.bottomRight(), crop.bottomLeft()
        ):
            painter.drawRoundedRect(
                QRectF(corner.x() - 4, corner.y() - 4, 8, 8), 2, 2
            )

        if self.image.width() > 0:
            crop_size = f"{int(self.crop.width())} × {int(self.crop.height())} px"
            painter.setPen(QColor(255, 255, 255, 190))
            painter.setFont(self.font())
            painter.drawText(
                QRectF(shown.left() + 8, shown.bottom() - 26, 260, 18),
                Qt.AlignLeft | Qt.AlignVCenter,
                crop_size,
            )

    # ------------------------------------------------------------------ mouse
    def _handles(self) -> dict[str, QPointF]:
        crop = self.to_widget(self.crop)
        return {
            "tl": crop.topLeft(),
            "tr": crop.topRight(),
            "br": crop.bottomRight(),
            "bl": crop.bottomLeft(),
        }

    def _hit(self, pos: QPointF) -> str | None:
        for name, point in self._handles().items():
            if abs(pos.x() - point.x()) <= self.HANDLE and abs(pos.y() - point.y()) <= self.HANDLE:
                return name
        if self.to_widget(self.crop).contains(pos):
            return "move"
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        hit = self._hit(event.position())
        if hit is None:
            return
        self._mode = hit
        self._start_crop = QRectF(self.crop)
        self._start_pos = event.position()
        if hit == "move":
            self.setCursor(Qt.ClosedHandCursor)
        else:
            self._anchor = self._anchor_for(hit)
            self._set_resize_cursor(hit)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._mode is None:
            hit = self._hit(event.position())
            self._cursor_for(hit)
            return
        pos = event.position()
        if self._mode == "move":
            factor = self.scale()
            delta = (pos - self._start_pos) / factor
            rect = QRectF(self._start_crop)
            rect.translate(delta)
            self.crop = self._clamp_move(rect)
        else:
            self.crop = self._resize_to(pos, self._mode)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._mode = None
        self._cursor_for(self._hit(event.position()))
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.reset_crop()

    def _cursor_for(self, hit: str | None) -> None:
        if hit in ("tl", "br"):
            self.setCursor(Qt.SizeFDiagCursor)
        elif hit in ("tr", "bl"):
            self.setCursor(Qt.SizeBDiagCursor)
        elif hit == "move":
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _set_resize_cursor(self, hit: str) -> None:
        self.setCursor(Qt.SizeFDiagCursor if hit in ("tl", "br") else Qt.SizeBDiagCursor)

    def _anchor_for(self, handle: str) -> QPointF:
        crop = self.crop
        return {
            "tl": crop.bottomRight(),
            "tr": crop.bottomLeft(),
            "br": crop.topLeft(),
            "bl": crop.topRight(),
        }[handle]

    def _clamp_move(self, rect: QRectF) -> QRectF:
        x = max(0.0, min(rect.x(), self.image.width() - rect.width()))
        y = max(0.0, min(rect.y(), self.image.height() - rect.height()))
        return QRectF(x, y, rect.width(), rect.height())

    def _resize_to(self, pos: QPointF, handle: str) -> QRectF:
        anchor = self._anchor
        mouse = self.to_image(pos)
        image_w = float(self.image.width())
        image_h = float(self.image.height())
        right = handle in ("tr", "br")
        down = handle in ("bl", "br")

        avail_w = image_w - anchor.x() if right else anchor.x()
        avail_h = image_h - anchor.y() if down else anchor.y()
        dx = (mouse.x() - anchor.x()) * (1 if right else -1)
        dy = (mouse.y() - anchor.y()) * (1 if down else -1)
        candidate = max(dx, dy * self.aspect)
        min_w = min(
            max(48.0, 36.0 / max(self.scale(), 0.001)),
            avail_w,
            avail_h * self.aspect,
        )
        width = max(min_w, min(candidate, avail_w, avail_h * self.aspect))
        height = width / self.aspect
        if height > avail_h:
            height = avail_h
            width = height * self.aspect
        x = anchor.x() if right else anchor.x() - width
        y = anchor.y() if down else anchor.y() - height
        return QRectF(x, y, width, height)


class BackgroundCropDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette, image: QImage,
                 aspect: float, accent: str = "#7F9CFF") -> None:
        super().__init__(
            parent, palette, "裁切背景",
            width=640, subtitle="拖动画面移动取景，拖四角缩放；比例自动锁到挂件",
        )
        self.setFixedHeight(650)
        self.cropped: QImage = QImage()

        self.canvas = CropCanvas(image, aspect, accent, self.body)
        self.canvas.setFixedHeight(430)
        self.add_widget(self.canvas)

        tip = label("双击取景框可以重置；图片不会被拉伸，只会按你框选的范围裁切。", "faint")
        tip.setWordWrap(True)
        self.add_widget(tip)

        self.add_button("取消", "ghost", self.reject)
        self.add_button("应用裁切", "accent", self._apply)

    def _apply(self) -> None:
        result = self.canvas.result_image()
        if result.isNull():
            return
        self.cropped = result
        self.accept()
