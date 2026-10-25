"""Sticky-note category management."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .dialogs import AlertDialog, ConfirmDialog, GlassDialog
from .notes import KIND_TEXT, KIND_TODO, Category, NoteStore
from .theme import Palette
from .ui.icons import dot_icon
from .ui.widgets import ColorSwatch, IconButton, label

CATEGORY_COLORS = [
    "#F2C879", "#7F9CFF", "#C3A6FF", "#7ED6C1",
    "#F49AC1", "#F08A7C", "#8FD3F4", "#A8E6A1",
]


class CategoryEditDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette,
                 category: Category | None = None) -> None:
        super().__init__(parent, palette, "编辑类别" if category else "新建类别", width=430,
                         subtitle="类别决定便签的默认类型与配色")
        self.category = category
        self.result_name = category.name if category else ""
        self.result_color = category.color if category else CATEGORY_COLORS[1]
        self.result_kind = category.kind if category else KIND_TEXT

        self.name_edit = QLineEdit(self.result_name, self.body)
        self.name_edit.setPlaceholderText("类别名称，例如：读书清单")
        self.name_edit.setMaxLength(24)
        self.add_widget(self.name_edit)

        self.error = label("", "faint")
        self.error.setStyleSheet("color: #F0736F;")
        self.error.hide()
        self.add_widget(self.error)

        color_title = label("颜色", "section")
        self.add_widget(color_title)
        colors = list(dict.fromkeys(CATEGORY_COLORS + [self.result_color]))
        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.setSpacing(4)
        self.color_group = QButtonGroup(self)
        for color in colors:
            swatch = ColorSwatch(color, selected=color.lower() == self.result_color.lower(),
                                 diameter=22, parent=self.body)
            swatch.clicked.connect(lambda checked=False, c=color: self._set_color(c))
            self.color_group.addButton(swatch)
            color_row.addWidget(swatch)
        color_row.addStretch(1)
        self.add_layout(color_row)

        kind_title = label("默认类型", "section")
        self.add_widget(kind_title)
        kind_host = QWidget(self.body)
        kind_host.setObjectName("transparent")
        kind_row = QHBoxLayout(kind_host)
        kind_row.setContentsMargins(0, 0, 0, 0)
        kind_row.setSpacing(6)
        self.kind_group = QButtonGroup(self)
        for index, (kind, text) in enumerate(((KIND_TEXT, "文本便签"), (KIND_TODO, "待办清单"))):
            button = QPushButton(text, kind_host)
            button.setObjectName("seg")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setChecked(self.result_kind == kind)
            self.kind_group.addButton(button, index)
            kind_row.addWidget(button)
        kind_row.addStretch(1)
        self.add_widget(kind_host)

        self.add_button("取消", "ghost", self.reject)
        self.add_button("保存", "accent", self._save)

    def _set_color(self, color: str) -> None:
        self.result_color = color

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.error.setText("请填写类别名称")
            self.error.show()
            self.name_edit.setFocus()
            return
        self.result_name = name
        checked = self.kind_group.checkedId()
        self.result_kind = KIND_TODO if checked == 1 else KIND_TEXT
        self.accept()


class CategoryRow(QFrame):
    def __init__(self, category: Category, count: int, palette: Palette,
                 on_edit, on_delete, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("noteRow")
        self.setAttribute(Qt.WA_Hover, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(9)

        dot = QLabel(self)
        dot.setPixmap(dot_icon(category.color, 12).pixmap(QSize(12, 12)))
        dot.setFixedWidth(14)
        layout.addWidget(dot)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(1)
        text.addWidget(label(category.name, "rowTitle"))
        kind_text = "待办清单" if category.kind == KIND_TODO else "文本便签"
        text.addWidget(label(f"{kind_text} · {count} 条便签", "faint"))
        layout.addLayout(text, 1)

        edit = IconButton("edit", palette.sub, 15, "编辑类别", self)
        edit.clicked.connect(lambda: on_edit(category))
        layout.addWidget(edit)
        delete = IconButton("trash", palette.faint, 15, "删除类别", self)
        delete.clicked.connect(lambda: on_delete(category))
        layout.addWidget(delete)


class CategoryDialog(GlassDialog):
    def __init__(self, parent: QWidget | None, palette: Palette, store: NoteStore) -> None:
        super().__init__(parent, palette, "便签类别", width=540,
                         subtitle="自定义类别名称、颜色和新建便签时的默认类型")
        self.store = store
        self.setFixedSize(540, 560)

        self.scroll = QScrollArea(self.body)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget(self.scroll)
        self.host.setObjectName("transparent")
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.host)
        self.add_widget(self.scroll)

        self.add_button("＋ 新建类别", "accent", self._add)
        self.add_button("关闭", "ghost", self.accept)

        self.store.changed.connect(self.refresh)
        self.refresh()

    def _count(self, category_id: str) -> int:
        return sum(1 for note in self.store.notes if note.category_id == category_id)

    def refresh(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for category in self.store.categories:
            row = CategoryRow(
                category,
                self._count(category.id),
                self.palette,
                self._edit,
                self._delete,
            )
            self.list_layout.addWidget(row)
        self.list_layout.addStretch(1)

    def _add(self) -> None:
        dialog = CategoryEditDialog(self, self.palette)
        if dialog.exec() == QDialog.Accepted:
            self.store.add_category(dialog.result_name, dialog.result_color, dialog.result_kind)

    def _edit(self, category: Category) -> None:
        dialog = CategoryEditDialog(self, self.palette, category)
        if dialog.exec() == QDialog.Accepted:
            self.store.update_category(
                category.id,
                name=dialog.result_name,
                color=dialog.result_color,
                kind=dialog.result_kind,
            )

    def _delete(self, category: Category) -> None:
        if len(self.store.categories) <= 1:
            AlertDialog.show_message(
                self, self.palette, "无法删除",
                "至少需要保留一个便签类别。可以先新建一个类别再删除这个。",
            )
            return
        count = self._count(category.id)
        fallback = next(c for c in self.store.categories if c.id != category.id)
        message = f"确定删除「{category.name}」吗？"
        if count:
            message += f"\n该类别下的 {count} 条便签会移动到「{fallback.name}」。"
        if ConfirmDialog.ask(self, self.palette, "删除类别", message, "删除", danger=True):
            self.store.delete_category(category.id)
