"""The always-on-top clock / weather widget."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..theme import Palette, palette_for
from ..weather import Weather
from .icons import icon as make_icon
from .icons import weather_pixmap
from .widgets import GlassCard, IconButton, Separator, apply_shadow

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
LUNAR_MONTHS = ["正月", "二月", "三月", "四月", "五月", "六月",
                "七月", "八月", "九月", "十月", "冬月", "腊月"]
LUNAR_DAYS = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]


def lunar_text(moment: datetime) -> str:
    try:
        from lunardate import LunarDate

        lunar = LunarDate.fromSolarDate(moment.year, moment.month, moment.day)
        month = ("闰" if getattr(lunar, "isLeapMonth", False) else "") + LUNAR_MONTHS[lunar.month - 1]
        return f"农历{month}{LUNAR_DAYS[lunar.day - 1]}"
    except Exception:
        return ""


def _font(size: float, weight: QFont.Weight = QFont.Normal,
          family: str = "Microsoft YaHei UI") -> QFont:
    font = QFont(family)
    font.setPointSizeF(size)
    font.setWeight(weight)
    return font


class TimeDisplay(QWidget):
    """Big time plus seconds, drawn on one shared baseline.

    Two QLabels cannot be reliably baseline-aligned: Qt aligns boxes, not
    text baselines, so the smaller seconds label floats upward. Painting both
    runs with the same baseline is exact and also bypasses app-level QSS fonts.
    """

    def __init__(self, palette: Palette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._palette = palette
        self._main = "--:--"
        self._seconds = ""
        self._ampm = ""
        self.setFixedHeight(58)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._resize_to_text()

    def set_palette(self, palette: Palette) -> None:
        self._palette = palette
        self.update()

    def set_time(self, main: str, seconds: str = "", ampm: str = "") -> None:
        if (main, seconds, ampm) == (self._main, self._seconds, self._ampm):
            return
        self._main = main
        self._seconds = seconds
        self._ampm = ampm
        self._resize_to_text()
        self.update()

    @staticmethod
    def _fonts() -> tuple[QFont, QFont, QFont]:
        return (
            _font(40, QFont.Light, "Segoe UI Light"),
            _font(14, QFont.Normal, "Segoe UI"),
            _font(8.5, QFont.Medium),
        )

    def _content_width(self) -> float:
        big, small, tiny = self._fonts()
        width = QFontMetrics(big).horizontalAdvance(self._main)
        if self._seconds:
            width += 3 + QFontMetrics(small).horizontalAdvance(self._seconds)
        if self._ampm:
            width += 6 + QFontMetrics(tiny).horizontalAdvance(self._ampm)
        return width

    def _resize_to_text(self) -> None:
        self.setFixedWidth(max(110, int(self._content_width()) + 2))

    def sizeHint(self) -> QSize:
        return QSize(max(110, int(self._content_width()) + 2), 58)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        big, small, tiny = self._fonts()
        baseline = self.height() - 8
        x = 0.0

        painter.setFont(big)
        painter.setPen(QColor(self._palette.text))
        painter.drawText(QPointF(x, baseline), self._main)
        x += QFontMetrics(big).horizontalAdvance(self._main)

        if self._seconds:
            painter.setFont(small)
            painter.setPen(QColor(self._palette.sub))
            painter.drawText(QPointF(x + 3, baseline), self._seconds)
            x += 3 + QFontMetrics(small).horizontalAdvance(self._seconds)

        if self._ampm:
            painter.setFont(tiny)
            painter.setPen(QColor(self._palette.faint))
            painter.drawText(QPointF(x + 6, baseline), self._ampm)


class ClockWidget(QWidget):
    settings_requested = Signal()
    city_requested = Signal()
    notes_requested = Signal()
    new_note_requested = Signal()
    refresh_requested = Signal()
    quit_requested = Signal()
    geometry_saved = Signal(int, int)
    transparency_adjusted = Signal(int)

    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.palette: Palette = palette_for(cfg.theme)
        self._weather: Weather | None = None
        self._drag_offset: QPoint | None = None
        self._first_show = True
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.setInterval(700)
        self._move_timer.timeout.connect(self._persist_position)

        self.setWindowTitle("Lumina Desk")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedWidth(356)
        self._apply_flags()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)

        self.card = GlassCard(self.palette, radius=26, opacity=cfg.transparency)
        self.card.set_accent(QColor(cfg.accent))
        apply_shadow(self.card, self.palette)
        outer.addWidget(self.card)

        body = QVBoxLayout(self.card)
        body.setContentsMargins(22, 19, 22, 18)
        body.setSpacing(0)

        # ---------------------------------------------------------------- header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(2)

        self.city_btn = QPushButton(cfg.city_name)
        self.city_btn.setObjectName("ghost")
        self.city_btn.setCursor(Qt.PointingHandCursor)
        self.city_btn.setToolTip("切换城市")
        self.city_btn.setFont(_font(9.5, QFont.Medium))
        self.city_btn.setIcon(make_icon("chevron_down", self.palette.faint, 12))
        self.city_btn.setIconSize(QSize(12, 12))
        self.city_btn.clicked.connect(self.city_requested)
        header.addWidget(self.city_btn)
        header.addStretch(1)

        self.refresh_btn = IconButton("refresh", self.palette.sub, 16, "刷新天气")
        self.refresh_btn.clicked.connect(self.refresh_requested)
        header.addWidget(self.refresh_btn)

        self.settings_btn = IconButton("gear", self.palette.sub, 16, "设置")
        self.settings_btn.clicked.connect(self.settings_requested)
        header.addWidget(self.settings_btn)
        body.addLayout(header)

        # ------------------------------------------------------------------ time
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 2, 0, 0)
        time_row.setSpacing(0)

        self.time_display = TimeDisplay(self.palette)
        time_row.addWidget(self.time_display, 0, Qt.AlignBottom)
        time_row.addStretch(1)
        body.addLayout(time_row)

        # ------------------------------------------------------------------ date
        self.date_label = QLabel("")
        self.date_label.setTextFormat(Qt.RichText)
        self.date_label.setFont(_font(9.5))
        self.date_label.setContentsMargins(1, 0, 0, 0)
        self.date_label.setFixedHeight(22)
        body.addWidget(self.date_label)

        # ------------------------------------------------------------- separator
        self.line = Separator(self._line_color())
        self.line.setContentsMargins(0, 0, 0, 0)
        separator_wrap = QVBoxLayout()
        separator_wrap.setContentsMargins(0, 12, 0, 12)
        separator_wrap.addWidget(self.line)
        body.addLayout(separator_wrap)

        # --------------------------------------------------------------- weather
        self.weather_block = QWidget()
        weather = QVBoxLayout(self.weather_block)
        weather.setContentsMargins(0, 0, 0, 0)
        weather.setSpacing(0)

        weather_top = QHBoxLayout()
        weather_top.setContentsMargins(0, 0, 0, 0)
        weather_top.setSpacing(10)

        self.weather_icon = QLabel()
        self.weather_icon.setFixedSize(54, 54)
        self.weather_icon.setAlignment(Qt.AlignCenter)
        weather_top.addWidget(self.weather_icon, 0, Qt.AlignVCenter)

        self.temp_label = QLabel("--°")
        self.temp_label.setFont(_font(29, QFont.Light, "Segoe UI Light"))
        self.temp_label.setStyleSheet(f"color: {self.palette.text}; background: transparent;")
        self.temp_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        weather_top.addWidget(self.temp_label)

        info = QVBoxLayout()
        info.setContentsMargins(2, 6, 0, 6)
        info.setSpacing(2)
        self.condition_label = QLabel("正在获取天气")
        self.condition_label.setFont(_font(10.5, QFont.Medium))
        self.condition_label.setStyleSheet(f"color: {self.palette.text}; background: transparent;")
        info.addWidget(self.condition_label)

        self.detail_label = QLabel("")
        self.detail_label.setFont(_font(8.5))
        self.detail_label.setStyleSheet(f"color: {self.palette.sub}; background: transparent;")
        info.addWidget(self.detail_label)
        weather_top.addLayout(info, 1)
        weather.addLayout(weather_top)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(1, 8, 0, 0)
        meta_row.setSpacing(6)
        self.meta_label = QLabel("")
        self.meta_label.setFont(_font(8))
        self.meta_label.setStyleSheet(f"color: {self.palette.faint}; background: transparent;")
        meta_row.addWidget(self.meta_label)
        meta_row.addStretch(1)
        self.updated_label = QLabel("")
        self.updated_label.setFont(_font(8))
        self.updated_label.setStyleSheet(f"color: {self.palette.faint}; background: transparent;")
        meta_row.addWidget(self.updated_label)
        weather.addLayout(meta_row)

        body.addWidget(self.weather_block)
        body.addSpacing(14)

        # ---------------------------------------------------------------- footer
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        self.notes_btn = QPushButton("便签 · 0")
        self.notes_btn.setObjectName("ghost")
        self.notes_btn.setCursor(Qt.PointingHandCursor)
        self.notes_btn.setFont(_font(9))
        self.notes_btn.setIcon(make_icon("note", self.palette.sub, 14))
        self.notes_btn.setIconSize(QSize(14, 14))
        self.notes_btn.clicked.connect(self.notes_requested)
        footer.addWidget(self.notes_btn)
        footer.addStretch(1)

        self.new_btn = QPushButton("新建便签")
        self.new_btn.setObjectName("accent")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.setFont(_font(9, QFont.DemiBold))
        self.new_btn.setFixedHeight(30)
        self.new_btn.setIcon(make_icon("plus", "#10131A", 14))
        self.new_btn.setIconSize(QSize(14, 14))
        self.new_btn.clicked.connect(self.new_note_requested)
        footer.addWidget(self.new_btn)
        body.addLayout(footer)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start()
        self._tick()

        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    # ------------------------------------------------------------------ helpers
    def _line_color(self) -> QColor:
        if self.palette.dark:
            return QColor(255, 255, 255, 24)
        return QColor(20, 28, 42, 22)

    def _apply_flags(self) -> None:
        flags = Qt.Tool | Qt.FramelessWindowHint
        if self.cfg.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _font_for(self, size: float, weight: QFont.Weight = QFont.Normal,
                  family: str = "Microsoft YaHei UI") -> QFont:
        return _font(size, weight, family)

    # -------------------------------------------------------------------- clock
    def _tick(self) -> None:
        now = datetime.now()
        if self.cfg.use_24h:
            main = now.strftime("%H:%M")
            ampm = ""
        else:
            main = now.strftime("%I:%M").lstrip("0") or "12:00"
            ampm = "上午" if now.hour < 12 else "下午"
        seconds = f":{now:%S}" if self.cfg.show_seconds else ""
        self.time_display.set_time(main, seconds, ampm)

        date_html = (
            f"<span style='color:{self.palette.sub}'>{now.month}月{now.day}日 "
            f"{WEEKDAYS[now.weekday()]}</span>"
        )
        if self.cfg.show_lunar:
            lunar = lunar_text(now)
            if lunar:
                date_html += f"<span style='color:{self.palette.faint}'> · {lunar}</span>"
        self.date_label.setText(date_html)
        self._update_position_if_off_screen(now)

    def _update_position_if_off_screen(self, now: datetime) -> None:
        # keep the widget reachable if the user unplugged a monitor
        if not self.isVisible():
            return
        screens = self.screen().availableGeometry() if self.screen() else None
        if screens is not None and not screens.intersects(self.frameGeometry()):
            self.move(screens.right() - self.width() - 40, screens.top() + 40)

    # ------------------------------------------------------------------ weather
    def set_loading(self) -> None:
        self.condition_label.setText("正在获取天气…")
        self.detail_label.setText("")
        self.meta_label.setText("")
        self.updated_label.setText("连接 Open-Meteo")
        if self._weather is None:
            self.temp_label.setText("--°")
            self.weather_icon.clear()

    def set_weather(self, weather: Weather, cached: bool = False) -> None:
        self._weather = weather
        self.temp_label.setText(f"{round(weather.temp)}°")
        self.condition_label.setText(weather.description)
        self.detail_label.setText(
            f"体感 {round(weather.feels)}° · 最高 {round(weather.tmax)}° / 最低 {round(weather.tmin)}°"
        )
        self.meta_label.setText(
            f"湿度 {weather.humidity}% · 风 {weather.wind:.1f} m/s"
        )
        prefix = "缓存 · " if cached else ""
        self.updated_label.setText(f"{prefix}更新于 {weather.fetched_label}")
        self.weather_icon.setPixmap(
            weather_pixmap(weather.icon, 54, self.palette.dark)
        )
        self.weather_icon.setToolTip(
            f"日出 {weather.sunrise or '--:--'} · 日落 {weather.sunset or '--:--'}"
        )
        self.weather_block.setToolTip(
            f"{weather.city} · {weather.description}\n"
            f"日出 {weather.sunrise or '--:--'} · 日落 {weather.sunset or '--:--'}"
        )

    def set_weather_error(self, message: str) -> None:
        self.condition_label.setText("天气暂时不可用")
        self.detail_label.setText("")
        self.meta_label.setText("")
        self.updated_label.setText("点击刷新重试")
        if self._weather is None:
            self.temp_label.setText("--°")
            self.weather_icon.clear()
        else:
            self.updated_label.setText(f"离线 · {self._weather.fetched_label}")
        self.weather_block.setToolTip(message)

    def set_note_count(self, count: int) -> None:
        self.notes_btn.setText(f"便签 · {count}")

    def set_city(self, name: str) -> None:
        self.city_btn.setText(name)

    # ------------------------------------------------------------------ theming
    def apply_theme(self, palette: Palette, accent: str) -> None:
        self.palette = palette
        self.cfg.accent = accent
        self.card.set_palette(palette)
        self.card.set_base(QColor(*palette.card))
        self.card.set_accent(QColor(accent))
        effect = self.card.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setColor(QColor(0, 0, 0, palette.shadow_alpha))
        else:
            apply_shadow(self.card, palette)

        self.time_display.set_palette(palette)
        self.temp_label.setStyleSheet(f"color: {palette.text}; background: transparent;")
        self.condition_label.setStyleSheet(f"color: {palette.text}; background: transparent;")
        self.detail_label.setStyleSheet(f"color: {palette.sub}; background: transparent;")
        self.meta_label.setStyleSheet(f"color: {palette.faint}; background: transparent;")
        self.updated_label.setStyleSheet(f"color: {palette.faint}; background: transparent;")
        self.line.set_color(self._line_color())

        self.city_btn.setIcon(make_icon("chevron_down", palette.faint, 12))
        self.refresh_btn.set_visual("refresh", palette.sub)
        self.settings_btn.set_visual("gear", palette.sub)
        self.notes_btn.setIcon(make_icon("note", palette.sub, 14))
        self.new_btn.setIcon(make_icon("plus", "#10131A", 14))

        if self._weather is not None:
            self.weather_icon.setPixmap(weather_pixmap(self._weather.icon, 54, palette.dark))
        self._tick()

    def apply_transparency(self, value: int) -> None:
        self.card.set_opacity(value)

    def set_always_on_top(self, enabled: bool) -> None:
        self.cfg.always_on_top = enabled
        visible = self.isVisible()
        self._apply_flags()
        if visible:
            self.show()
            self.raise_()

    # ------------------------------------------------------------------ events
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setWindowOpacity(0.0)
            self._fade = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade.setDuration(220)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.setEasingCurve(QEasingCurve.OutCubic)
            self._fade.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self._drag_offset = None
            self._move_timer.start()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        if self.isVisible():
            self._move_timer.start()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.notes_requested.emit()
            event.accept()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            step = 4 if event.angleDelta().y() > 0 else -4
            value = max(10, min(100, self.cfg.transparency + step))
            if value != self.cfg.transparency:
                self.cfg.transparency = value
                self.card.set_opacity(value)
                self.transparency_adjusted.emit(value)
            event.accept()
        else:
            super().wheelEvent(event)

    def _persist_position(self) -> None:
        if self.isVisible() and self.pos().x() > -30000:
            self.geometry_saved.emit(self.x(), self.y())

    def _context_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("新建便签", self.new_note_requested.emit)
        menu.addAction("便签管理…", self.notes_requested.emit)
        menu.addSeparator()
        menu.addAction("刷新天气", self.refresh_requested.emit)
        menu.addAction("设置…", self.settings_requested.emit)
        menu.addSeparator()
        hide_action = menu.addAction("隐藏到托盘", self.hide)
        hide_action.setEnabled(self.isVisible())
        menu.addAction("退出 Lumina Desk", self.quit_requested.emit)
        menu.exec(self.mapToGlobal(position))
