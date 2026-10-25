"""Settings and city picker dialogs."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .background import background_path, load_image, save_background
from .config import ACCENTS, Config
from .dialogs import AlertDialog, GlassDialog
from .image_crop import BackgroundCropDialog
from .paths import VERSION, data_dir
from .theme import Palette, palette_for
from .ui.widgets import ColorSwatch, SectionTitle, ToggleSwitch, label
from .weather import WeatherService


def _row(title: str, hint: str = "") -> tuple[QWidget, QHBoxLayout]:
    host = QWidget()
    host.setObjectName("transparent")
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    text = QVBoxLayout()
    text.setContentsMargins(0, 0, 0, 0)
    text.setSpacing(1)
    text.addWidget(label(title, "sub"))
    if hint:
        faint = label(hint, "faint")
        faint.setWordWrap(True)
        text.addWidget(faint)
    row.addLayout(text, 1)
    return host, row


class CityRow(QFrame):
    def __init__(self, city: dict, parent: QWidget, on_choose) -> None:
        super().__init__(parent)
        self.city = city
        self._on_choose = on_choose
        self.setObjectName("noteRow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(1)
        titles.addWidget(label(city["name"], "rowTitle"))
        detail = " · ".join(
            part for part in (city.get("admin1"), city.get("country")) if part
        )
        titles.addWidget(label(detail or "—", "faint"))
        layout.addLayout(titles, 1)
        coords = label(f"{city['latitude']:.2f}, {city['longitude']:.2f}", "faint")
        layout.addWidget(coords, 0, Qt.AlignRight)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._on_choose(self.city)
        super().mouseReleaseEvent(event)


class CitySearchDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette, current: str) -> None:
        super().__init__(parent, palette, "选择城市", width=470,
                         subtitle="通过 Open-Meteo 地理编码搜索全球城市")
        self.setFixedHeight(520)
        self.choice: dict | None = None
        self.service = WeatherService(self)
        self.service.cities.connect(self._on_cities)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        self.query = QLineEdit(current, self.body)
        self.query.setPlaceholderText("输入城市名，例如：杭州、Tokyo、New York")
        self.query.setClearButtonEnabled(True)
        self.query.returnPressed.connect(self._search)
        search_row.addWidget(self.query, 1)
        self.search_btn = QPushButton("搜索", self.body)
        self.search_btn.setObjectName("accent")
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_btn)
        self.add_layout(search_row)

        self.status = label("输入城市名后回车搜索", "faint")
        self.add_widget(self.status)

        self.scroll = QScrollArea(self.body)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget(self.scroll)
        self.host.setObjectName("transparent")
        self.results_layout = QVBoxLayout(self.host)
        self.results_layout.setContentsMargins(0, 0, 4, 0)
        self.results_layout.setSpacing(6)
        self.scroll.setWidget(self.host)
        self.add_widget(self.scroll)

        self.add_button("取消", "ghost", self.reject)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.query.setFocus()
        self.query.selectAll()
        QTimer.singleShot(80, self._search)

    def _search(self) -> None:
        text = self.query.text().strip()
        if not text:
            return
        self.status.setText("正在搜索…")
        self.search_btn.setEnabled(False)
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.service.search_city(text)

    def _on_cities(self, cities: list[dict]) -> None:
        self.search_btn.setEnabled(True)
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not cities:
            self.status.setText("没有找到匹配的城市，换个关键词试试")
            self.results_layout.addStretch(1)
            return
        self.status.setText(f"找到 {len(cities)} 个结果，点击即可切换")
        for city in cities:
            self.results_layout.addWidget(CityRow(city, self.host, self._choose))
        self.results_layout.addStretch(1)

    def _choose(self, city: dict) -> None:
        self.choice = city
        self.accept()


class SettingsDialog(GlassDialog):
    changed = Signal()
    categories_requested = Signal()
    preview_requested = Signal()

    def __init__(self, parent: QWidget | None, palette: Palette, cfg: Config,
                 background_ratio: float = 356 / 340) -> None:
        super().__init__(parent, palette, "设置", width=480,
                         subtitle="外观、天气与桌面行为")
        self.cfg = cfg
        self._background_ratio = max(0.4, min(3.0, background_ratio))
        self.setFixedSize(480, 930)

        content = QWidget(self.body)
        content.setObjectName("transparent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)

        # ---------------------------------------------------------- weather
        layout.addWidget(SectionTitle("城市与天气"))
        city_host, city_row = _row("当前城市", "天气每 15 分钟自动刷新，也可在挂件上点击刷新")
        self.city_btn = QPushButton("", city_host)
        self.city_btn.setCursor(Qt.PointingHandCursor)
        self.city_btn.clicked.connect(self._pick_city)
        city_row.addWidget(self.city_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(city_host)
        self._sync_city_button()

        interval_host, interval_row = _row("刷新间隔")
        self.interval = QComboBox(interval_host)
        for minutes in (5, 10, 15, 30, 60):
            self.interval.addItem(f"{minutes} 分钟", minutes)
        index = self.interval.findData(cfg.refresh_minutes)
        self.interval.setCurrentIndex(max(0, index))
        self.interval.currentIndexChanged.connect(self._interval_changed)
        interval_row.addWidget(self.interval)
        layout.addWidget(interval_host)

        # --------------------------------------------------------- appearance
        layout.addSpacing(6)
        layout.addWidget(SectionTitle("外观"))
        theme_host, theme_row = _row("主题")
        self.theme_group = QButtonGroup(self)
        for index, (name, text) in enumerate((("dark", "深色"), ("light", "浅色"))):
            button = QPushButton(text, theme_host)
            button.setObjectName("seg")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setChecked(cfg.theme == name)
            self.theme_group.addButton(button, index)
            theme_row.addWidget(button)
        self.theme_group.idClicked.connect(
            lambda index: self._theme_changed("dark" if index == 0 else "light")
        )
        layout.addWidget(theme_host)

        accent_host, accent_row = _row("强调色")
        self.accent_group = QButtonGroup(self)
        self._swatches: list[ColorSwatch] = []
        for color in ACCENTS:
            swatch = ColorSwatch(color, selected=color.lower() == cfg.accent.lower(), parent=accent_host)
            swatch.clicked.connect(lambda checked=False, c=color: self._accent_changed(c))
            self.accent_group.addButton(swatch)
            self._swatches.append(swatch)
            accent_row.addWidget(swatch)
        layout.addWidget(accent_host)

        # ---------------------------------------------------------- background
        layout.addSpacing(6)
        layout.addWidget(SectionTitle("背景"))
        background_host, background_row = _row(
            "自定义背景", "按挂件比例裁切，文字保持可读"
        )
        self.background_btn = QPushButton("选择图片…", background_host)
        self.background_btn.setCursor(Qt.PointingHandCursor)
        self.background_btn.clicked.connect(self._choose_background)
        background_row.addWidget(self.background_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.background_reset = QPushButton("恢复默认", background_host)
        self.background_reset.setObjectName("chip")
        self.background_reset.setCursor(Qt.PointingHandCursor)
        self.background_reset.clicked.connect(self._reset_background)
        background_row.addWidget(self.background_reset, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(background_host)

        preview_host = QWidget(content)
        preview_host.setObjectName("transparent")
        preview_row = QHBoxLayout(preview_host)
        preview_row.setContentsMargins(0, 0, 0, 0)
        preview_row.setSpacing(10)
        self.background_preview = QLabel(preview_host)
        self.background_preview.setObjectName("bgPreview")
        self.background_preview.setFixedSize(92, 52)
        self.background_preview.setAlignment(Qt.AlignCenter)
        preview_row.addWidget(self.background_preview)

        background_info = QVBoxLayout()
        background_info.setContentsMargins(0, 0, 0, 0)
        background_info.setSpacing(1)
        self.background_state = label("默认渐变背景", "sub")
        background_info.addWidget(self.background_state)
        background_info.addWidget(label("裁切结果会另存到数据目录", "faint"))
        preview_row.addLayout(background_info, 1)

        layout.addWidget(preview_host)
        self._sync_background()

        transparency_host, transparency_row = _row("背景透明度", "数值越高越不透明；也可在挂件上 Ctrl+滚轮调节")
        self.transparency_value = label(f"{cfg.transparency}%", "faint")
        self.transparency = QSlider(Qt.Horizontal, transparency_host)
        self.transparency.setRange(25, 100)
        self.transparency.setValue(cfg.transparency)
        self.transparency.setFixedWidth(170)
        self.transparency.valueChanged.connect(self._transparency_changed)
        transparency_row.addWidget(self.transparency)
        transparency_row.addWidget(self.transparency_value)
        layout.addWidget(transparency_host)

        self.seconds_toggle = self._toggle_row(layout, "显示秒数", cfg.show_seconds)
        self.lunar_toggle = self._toggle_row(layout, "显示农历", cfg.show_lunar)

        # ---------------------------------------------------------- behaviour
        layout.addSpacing(6)
        layout.addWidget(SectionTitle("窗口与启动"))
        self.topmost_toggle = self._toggle_row(layout, "窗口始终置顶", cfg.always_on_top)
        self.autostart_toggle = self._toggle_row(
            layout, "开机自动启动", cfg.autostart, "登录 Windows 后自动显示挂件"
        )

        # -------------------------------------------------------------- notes
        layout.addSpacing(6)
        layout.addWidget(SectionTitle("便签"))
        note_host, note_row = _row("便签类别", "自定义类别名称、颜色与默认类型")
        manage_btn = QPushButton("管理类别…", note_host)
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.clicked.connect(self.categories_requested.emit)
        note_row.addWidget(manage_btn)
        layout.addWidget(note_host)

        # -------------------------------------------------------------- about
        layout.addSpacing(6)
        layout.addWidget(SectionTitle("关于"))
        about = label(
            f"Lumina Desk {VERSION} · 桌面时钟、天气与便签\n"
            f'数据保存在 <span style="color:{palette.sub}">{data_dir()}</span>',
            "faint",
        )
        about.setWordWrap(True)
        about.setTextFormat(Qt.RichText)
        layout.addWidget(about)

        links = QHBoxLayout()
        links.setContentsMargins(0, 0, 0, 0)
        links.setSpacing(8)
        repo = QLabel(
            f'<a href="{self._repo_url()}" style="color:{cfg.accent}; text-decoration:none;">'
            "GitHub 仓库</a>"
        )
        repo.setOpenExternalLinks(True)
        repo.setTextFormat(Qt.RichText)
        links.addWidget(repo)
        folder = QPushButton("打开数据目录", self)
        folder.setObjectName("ghost")
        folder.setCursor(Qt.PointingHandCursor)
        folder.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))
        )
        links.addWidget(folder)
        links.addStretch(1)
        layout.addLayout(links)
        layout.addStretch(1)

        scroll = QScrollArea(self.body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.add_widget(scroll)

        self.add_button("取消", "ghost", self.reject)
        self.add_button("保存", "accent", self.accept)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _repo_url() -> str:
        from .paths import REPO_URL

        return REPO_URL

    def _toggle_row(self, layout: QVBoxLayout, title: str, checked: bool,
                    hint: str = "") -> ToggleSwitch:
        host, row = _row(title, hint)
        toggle = ToggleSwitch(checked, host)
        toggle.setProperty("accent", self.cfg.accent)
        toggle.setProperty("dark", self.palette.dark)
        toggle.toggled.connect(self._toggles_changed)
        row.addWidget(toggle, 0, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(host)
        return toggle

    def _sync_city_button(self) -> None:
        self.city_btn.setText(f"{self.cfg.city_name}  ›")
        self.city_btn.setToolTip(
            f"{self.cfg.latitude:.4f}, {self.cfg.longitude:.4f} · {self.cfg.timezone}"
        )

    def _pick_city(self) -> None:
        dialog = CitySearchDialog(self, self.palette, self.cfg.city_name)
        if dialog.exec() == QDialog.Accepted and dialog.choice is not None:
            city = dialog.choice
            self.cfg.city_name = city["name"]
            self.cfg.latitude = float(city["latitude"])
            self.cfg.longitude = float(city["longitude"])
            self.cfg.timezone = str(city.get("timezone") or "auto")
            self._sync_city_button()
            self.changed.emit()

    def _interval_changed(self) -> None:
        value = self.interval.currentData()
        if value:
            self.cfg.refresh_minutes = int(value)
            self.changed.emit()

    def _theme_changed(self, name: str) -> None:
        if name == self.cfg.theme:
            return
        self.cfg.theme = name
        self.palette = palette_for(name)
        self.card.set_palette(self.palette)
        self.card.set_base(QColor(*self.palette.dialog))
        for toggle in (self.seconds_toggle, self.lunar_toggle,
                       self.topmost_toggle, self.autostart_toggle):
            toggle.setProperty("dark", self.palette.dark)
            toggle.update()
        self.changed.emit()

    def _accent_changed(self, color: str) -> None:
        if color.lower() == self.cfg.accent.lower():
            return
        self.cfg.accent = color
        for toggle in (self.seconds_toggle, self.lunar_toggle,
                       self.topmost_toggle, self.autostart_toggle):
            toggle.setProperty("accent", color)
            toggle.update()
        self.changed.emit()

    def _choose_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        image = load_image(path)
        if image.isNull():
            AlertDialog.show_message(
                self, self.palette, "无法读取图片",
                "这个文件不是可识别的图片，或格式不受支持。请换一张 PNG / JPG / WebP 图片。",
            )
            return
        dialog = BackgroundCropDialog(
            self, self.palette, image, self._background_ratio, self.cfg.accent
        )
        if dialog.exec() != QDialog.Accepted or dialog.cropped.isNull():
            return
        try:
            name = save_background(dialog.cropped)
        except OSError as exc:
            AlertDialog.show_message(self, self.palette, "保存失败", str(exc))
            return
        self.cfg.background_file = name
        self._sync_background()
        self.changed.emit()

    def _reset_background(self) -> None:
        if not self.cfg.background_file:
            return
        self.cfg.background_file = ""
        self._sync_background()
        self.changed.emit()

    def _sync_background(self) -> None:
        path = background_path(self.cfg)
        pixmap = QPixmap(str(path)) if path is not None else QPixmap()
        if not pixmap.isNull():
            target = self.background_preview.size()
            scaled = pixmap.scaled(
                target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = max(0, (scaled.width() - target.width()) // 2)
            y = max(0, (scaled.height() - target.height()) // 2)
            self.background_preview.setPixmap(
                scaled.copy(x, y, target.width(), target.height())
            )
            self.background_state.setText("自定义图片")
            self.background_reset.setVisible(True)
        else:
            self.background_preview.clear()
            self.background_preview.setText("默认")
            self.background_state.setText("默认渐变背景")
            self.background_reset.setVisible(False)

    def _transparency_changed(self, value: int) -> None:
        self.cfg.transparency = value
        self.transparency_value.setText(f"{value}%")
        self.changed.emit()

    def _toggles_changed(self) -> None:
        self.cfg.show_seconds = self.seconds_toggle.isChecked()
        self.cfg.show_lunar = self.lunar_toggle.isChecked()
        self.cfg.always_on_top = self.topmost_toggle.isChecked()
        self.cfg.autostart = self.autostart_toggle.isChecked()
        self.changed.emit()
