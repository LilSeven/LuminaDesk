"""Note manager: search, filter by category, open or delete sticky notes."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .dialogs import GlassDialog
from .notes import Category, Note, NoteStore
from .theme import Palette
from .ui.icons import dot_icon, icon as make_icon
from .ui.widgets import IconButton, label


def _stamp(iso: str) -> str:
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    now = datetime.now()
    if moment.date() == now.date():
        return moment.strftime("今天 %H:%M")
    if moment.year == now.year:
        return moment.strftime("%m月%d日 %H:%M")
    return moment.strftime("%Y-%m-%d")


class NoteRow(QFrame):
    def __init__(self, note: Note, category: Category | None, palette: Palette,
                 on_open, on_delete, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note = note
        self._on_open = on_open
        self.setObjectName("noteRow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 10, 8, 10)
        layout.setSpacing(10)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(3)

        title = note.title.strip() or "无标题便签"
        self.title_label = label(title, "noteTitle")
        self.title_label.setToolTip(title)
        text_column.addWidget(self.title_label)

        preview = label(note.preview(110), "notePreview")
        preview.setWordWrap(True)
        text_column.addWidget(preview)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 1, 0, 0)
        meta.setSpacing(5)
        if category is not None:
            dot = QLabel(self)
            dot.setPixmap(dot_icon(category.color, 8).pixmap(QSize(8, 8)))
            meta.addWidget(dot)
            meta.addWidget(label(category.name, "faint"))
            meta.addWidget(label("·", "faint"))
        meta.addWidget(label(_stamp(note.updated_at), "faint"))
        if note.open_window:
            meta.addWidget(label("·", "faint"))
            meta.addWidget(label("窗口已打开", "faint"))
        meta.addStretch(1)
        text_column.addLayout(meta)
        layout.addLayout(text_column, 1)

        self.delete_btn = IconButton("trash", palette.faint, 15, "删除便签", self)
        self.delete_btn.clicked.connect(lambda: on_delete(note.id))
        layout.addWidget(self.delete_btn, 0, Qt.AlignTop)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._on_open(self.note.id)
        super().mouseReleaseEvent(event)


class NoteManager(GlassDialog):
    open_requested = Signal(str)
    delete_requested = Signal(str)
    new_note_requested = Signal(str)
    categories_requested = Signal()

    def __init__(self, parent: QWidget | None, palette: Palette, store: NoteStore) -> None:
        super().__init__(parent, palette, "便签中心", width=700,
                         subtitle="搜索、整理并打开你的所有便签")
        self.store = store
        self.setFixedSize(700, 590)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        self.search = QLineEdit(self.body)
        self.search.setPlaceholderText("搜索标题、内容或待办事项…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.category_filter = QComboBox(self.body)
        self.category_filter.setFixedWidth(132)
        self.category_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.category_filter)

        self.new_btn = QPushButton("新建便签", self.body)
        self.new_btn.setObjectName("accent")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.clicked.connect(self._new_note)
        toolbar.addWidget(self.new_btn)
        self.add_layout(toolbar)

        self.scroll = QScrollArea(self.body)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget(self.scroll)
        self.host.setObjectName("transparent")
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(0, 2, 4, 2)
        self.list_layout.setSpacing(7)
        self.scroll.setWidget(self.host)
        self.add_widget(self.scroll)

        self.add_button("类别管理", "ghost", self.categories_requested.emit)
        self.add_button("关闭", "ghost", self.reject)

        self.store.changed.connect(self.refresh)
        self._fill_categories()
        self.refresh()

    # ------------------------------------------------------------------ data
    def _fill_categories(self) -> None:
        current = self.category_filter.currentData()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem(dot_icon("#A4ADBC", 9), "全部类别", "")
        for category in self.store.categories:
            self.category_filter.addItem(dot_icon(category.color, 9), category.name, category.id)
        index = self.category_filter.findData(current)
        self.category_filter.setCurrentIndex(max(0, index))
        self.category_filter.blockSignals(False)

    def _matches(self, note: Note, text: str) -> bool:
        if not text:
            return True
        haystack = [note.title, note.body]
        haystack.extend(item.text for item in note.todos)
        category = self.store.category(note.category_id)
        if category is not None:
            haystack.append(category.name)
        return any(text in value.lower() for value in haystack)

    def refresh(self) -> None:
        if self.category_filter.count() == 0:
            self._fill_categories()
        category_id = self.category_filter.currentData() or ""
        needle = self.search.text().strip().lower()

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        notes = [
            note for note in self.store.sorted_notes()
            if (not category_id or note.category_id == category_id)
            and self._matches(note, needle)
        ]
        total = self.store.count()
        if notes:
            for note in notes:
                row = NoteRow(
                    note,
                    self.store.category(note.category_id),
                    self.palette,
                    self._open,
                    self._delete,
                )
                self.list_layout.addWidget(row)
            self.list_layout.addStretch(1)
            self.subtitle_label.setText(f"共 {total} 条便签 · 当前显示 {len(notes)} 条")
        else:
            self.list_layout.addStretch(1)
            empty = label(
                "没有找到便签" if total else "还没有便签，点右上角「新建便签」开始",
                "emptyHint",
            )
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch(1)
            self.subtitle_label.setText(f"共 {total} 条便签")

    # -----------------------------------------------------------------action
    def _open(self, note_id: str) -> None:
        self.open_requested.emit(note_id)

    def _delete(self, note_id: str) -> None:
        self.delete_requested.emit(note_id)

    def _new_note(self) -> None:
        self.new_note_requested.emit(self.category_filter.currentData() or "")

    def showEvent(self, event) -> None:  # noqa: N802
        self._fill_categories()
        self.refresh()
        super().showEvent(event)
