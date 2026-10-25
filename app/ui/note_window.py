"""Frameless sticky-note window: editable title, text or checklist body."""
from __future__ import annotations

import time
import uuid
from datetime import datetime

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..dialogs import ConfirmDialog
from ..notes import KIND_TEXT, KIND_TODO, Note, NoteStore, TodoItem
from ..theme import Palette, note_color
from .icons import dot_icon, icon as make_icon
from .widgets import (
    DragBar,
    GlassCard,
    IconButton,
    Separator,
    apply_shadow,
    hbox,
    label,
    vbox,
)


def _short_time(timestamp: str | float) -> str:
    try:
        if isinstance(timestamp, str):
            moment = datetime.fromisoformat(timestamp)
        else:
            moment = datetime.fromtimestamp(timestamp)
        return moment.strftime("%H:%M")
    except (OSError, ValueError, TypeError):
        return "--:--"


class RoundCheck(QAbstractButton):
    """Small circular check button used by checklist rows."""

    def __init__(self, checked: bool, palette: Palette, accent: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.palette = palette
        self.accent = accent
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(19, 19)
        self.setToolTip("标记完成")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        if self.isChecked():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self.accent))
            painter.drawEllipse(rect)
            pen = QPen(QColor("#FFFFFF"), 1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(rect.left() + 4.2, rect.top() + 8.4)
            path.lineTo(rect.left() + 7.2, rect.top() + 11.2)
            path.lineTo(rect.left() + 12.0, rect.top() + 5.6)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        else:
            color = QColor(self.palette.sub)
            color.setAlpha(150)
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect)


class TodoRow(QWidget):
    def __init__(self, item: TodoItem, palette: Palette, accent: str,
                 on_toggle, on_text, on_delete, on_enter,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.palette = palette
        self._on_toggle = on_toggle
        self._on_text = on_text
        self._on_delete = on_delete
        self._on_enter = on_enter

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.setSpacing(7)

        self.check = RoundCheck(item.done, palette, accent)
        self.check.toggled.connect(self._toggled)
        row.addWidget(self.check, 0, Qt.AlignTop)

        self.edit = QLineEdit(item.text)
        self.edit.setObjectName("todoEdit")
        self.edit.setPlaceholderText("事项内容")
        self.edit.setFrame(False)
        self.edit.textEdited.connect(self._text_changed)
        self.edit.returnPressed.connect(lambda: self._on_enter(self.item))
        self.edit.editingFinished.connect(self._editing_finished)
        row.addWidget(self.edit, 1)

        self.delete_btn = IconButton("close", palette.faint, 11, "删除这一项", self)
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.clicked.connect(lambda: self._on_delete(self.item))
        row.addWidget(self.delete_btn, 0, Qt.AlignTop)

        self._apply_done_style()

    def _toggled(self, checked: bool) -> None:
        self.item.done = checked
        self._apply_done_style()
        self._on_toggle(self.item, checked)

    def _text_changed(self, text: str) -> None:
        self.item.text = text
        self._on_text(self.item, text)

    def _editing_finished(self) -> None:
        if not self.item.text.strip():
            self._on_delete(self.item)

    def _apply_done_style(self) -> None:
        font = self.edit.font()
        font.setStrikeOut(self.item.done)
        self.edit.setFont(font)
        self.edit.setStyleSheet(
            f"color: {self.palette.faint};" if self.item.done else ""
        )

    def focus_editor(self) -> None:
        self.edit.setFocus()
        self.edit.setCursorPosition(len(self.edit.text()))


class NoteWindow(QWidget):
    delete_requested = Signal(str)
    categories_requested = Signal()
    new_note_requested = Signal()

    def __init__(self, store: NoteStore, note: Note, palette: Palette,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.note = note
        self.palette = palette
        self._rows: list[TodoRow] = []
        self._dirty = False
        self._geometry_ready = False

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(252, 196)
        self.setWindowTitle(f"便签 · {note.title or '无标题'}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        category = store.category(note.category_id)
        base = note_color(palette, category.color if category else "#7F9CFF")
        accent = category.color if category else "#7F9CFF"

        self.card = GlassCard(palette, radius=20, opacity=96, base=base)
        self.card.set_accent(QColor(accent))
        apply_shadow(self.card, palette, blur=36, y=10)
        outer.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 12, 16, 10)
        card_layout.setSpacing(7)

        # header ---------------------------------------------------------
        self.header = DragBar(self, self.card)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        self.chip = QPushButton("", self.header)
        self.chip.setObjectName("chip")
        self.chip.setCursor(Qt.PointingHandCursor)
        self.chip.setIconSize(QSize(8, 8))
        self.chip.setFixedHeight(23)
        self.chip.setToolTip("切换便签类别")
        self.chip.clicked.connect(self._show_category_menu)
        header_layout.addWidget(self.chip, 0, Qt.AlignLeft)
        header_layout.addStretch(1)

        self.pin_btn = IconButton("pin_off", palette.sub, 15, "置顶窗口", self.header)
        self.pin_btn.clicked.connect(self._toggle_pin)
        header_layout.addWidget(self.pin_btn)

        self.more_btn = IconButton("more", palette.sub, 16, "更多操作", self.header)
        self.more_btn.clicked.connect(self._show_more_menu_at_button)
        header_layout.addWidget(self.more_btn)

        self.close_btn = IconButton("close", palette.sub, 15, "收起便签", self.header)
        self.close_btn.clicked.connect(self.hide_note)
        header_layout.addWidget(self.close_btn)

        card_layout.addWidget(self.header)

        # title ----------------------------------------------------------
        self.title_edit = QLineEdit(note.title, self.card)
        self.title_edit.setObjectName("titleEdit")
        self.title_edit.setPlaceholderText("无标题便签")
        self.title_edit.setMaxLength(80)
        self.title_edit.setFixedHeight(24)
        self.title_edit.textChanged.connect(self._title_changed)
        self.title_edit.editingFinished.connect(self._flush)
        card_layout.addWidget(self.title_edit)

        # body -----------------------------------------------------------
        self.stack = QStackedWidget(self.card)
        self.stack.setAttribute(Qt.WA_TranslucentBackground, True)

        self.text_page = QWidget(self.stack)
        self.text_page.setObjectName("transparent")
        text_layout = QVBoxLayout(self.text_page)
        text_layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QTextEdit(self.text_page)
        self.editor.setObjectName("noteBody")
        self.editor.setAcceptRichText(False)
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setPlaceholderText("写点什么…\n内容会自动保存")
        self.editor.setPlainText(note.body)
        self.editor.textChanged.connect(self._body_changed)
        text_layout.addWidget(self.editor)
        self.stack.addWidget(self.text_page)

        self.todo_page = QWidget(self.stack)
        self.todo_page.setObjectName("transparent")
        todo_layout = QVBoxLayout(self.todo_page)
        todo_layout.setContentsMargins(0, 0, 0, 0)
        todo_layout.setSpacing(6)

        self.todo_scroll = QScrollArea(self.todo_page)
        self.todo_scroll.setWidgetResizable(True)
        self.todo_scroll.setFrameShape(QFrame.NoFrame)
        self.todo_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.todo_host = QWidget(self.todo_scroll)
        self.todo_host.setObjectName("transparent")
        self.todo_layout = QVBoxLayout(self.todo_host)
        self.todo_layout.setContentsMargins(0, 0, 2, 0)
        self.todo_layout.setSpacing(3)
        self.todo_scroll.setWidget(self.todo_host)
        todo_layout.addWidget(self.todo_scroll, 1)

        todo_layout.addWidget(Separator(QColor(palette.border)))
        self.todo_input = QLineEdit(self.todo_page)
        self.todo_input.setObjectName("addTodo")
        self.todo_input.setPlaceholderText("＋ 添加一项，回车确认")
        self.todo_input.setFrame(False)
        self.todo_input.returnPressed.connect(self._add_todo_from_input)
        todo_layout.addWidget(self.todo_input)
        self.stack.addWidget(self.todo_page)

        card_layout.addWidget(self.stack, 1)

        # footer ---------------------------------------------------------
        self.footer = QWidget(self.card)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(4)
        self.meta = label("", "noteMeta")
        footer_layout.addWidget(self.meta)
        footer_layout.addStretch(1)
        self.grip = QSizeGrip(self.footer)
        self.grip.setFixedSize(14, 14)
        footer_layout.addWidget(self.grip, 0, Qt.AlignBottom | Qt.AlignRight)
        card_layout.addWidget(self.footer)

        # timers ---------------------------------------------------------
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(550)
        self._save_timer.timeout.connect(self._flush)

        self._geom_timer = QTimer(self)
        self._geom_timer.setSingleShot(True)
        self._geom_timer.setInterval(700)
        self._geom_timer.timeout.connect(self._save_geometry)

        self._apply_category()
        self._apply_kind()
        self._apply_pin()
        self._update_meta()
        self._place_window(note)

    # ------------------------------------------------------------------ layout
    def _place_window(self, note: Note) -> None:
        screen = None
        if note.x is not None and note.y is not None:
            screen = QApplication.screenAt(QPoint(int(note.x), int(note.y)))
        if screen is None:
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = int(note.width or 300)
        height = int(note.height or 320)
        width = max(252, min(width, available.width() - 24))
        height = max(196, min(height, available.height() - 24))
        if note.x is None or note.y is None:
            point = QCursor.pos()
            x = point.x() - 130
            y = point.y() - 30
        else:
            x, y = int(note.x), int(note.y)
        x = max(available.left() + 8, min(x, available.right() - width - 8))
        y = max(available.top() + 8, min(y, available.bottom() - height - 8))
        self.setGeometry(x, y, width, height)
        note.x, note.y, note.width, note.height = x, y, width, height

    # ------------------------------------------------------------------- data
    def _title_changed(self, text: str) -> None:
        self.note.title = text
        self.setWindowTitle(f"便签 · {text or '无标题'}")
        self._mark_dirty()

    def _body_changed(self) -> None:
        self.note.body = self.editor.toPlainText()
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.note.touch()
        self._save_timer.start()

    def _flush(self) -> None:
        if not self._dirty:
            return
        self._save_timer.stop()
        self.store.save()
        self._dirty = False
        self._update_meta()

    def _update_meta(self) -> None:
        parts: list[str] = []
        if self.note.kind == KIND_TODO:
            done, total = self.note.progress()
            parts.append(f"{done}/{total} 已完成")
        parts.append(f"已保存 {_short_time(self.note.updated_at)}")
        self.meta.setText(" · ".join(parts))

    # ------------------------------------------------------------------- kind
    def _apply_kind(self) -> None:
        if self.note.kind == KIND_TODO:
            self.stack.setCurrentWidget(self.todo_page)
            self._rebuild_todos()
        else:
            self.stack.setCurrentWidget(self.text_page)
            self.editor.blockSignals(True)
            if self.editor.toPlainText() != self.note.body:
                self.editor.setPlainText(self.note.body)
            self.editor.blockSignals(False)

    def _rebuild_todos(self) -> None:
        while self.todo_layout.count():
            item = self.todo_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

        if not self.note.todos:
            hint = label("还没有事项，在下面输入后按回车添加", "emptyHint")
            hint.setWordWrap(True)
            self.todo_layout.addWidget(hint)
        else:
            for entry in self.note.todos:
                row = TodoRow(
                    entry,
                    self.palette,
                    self._accent(),
                    self._todo_toggled,
                    self._todo_text,
                    self._delete_todo,
                    self._add_todo_after,
                )
                self.todo_layout.addWidget(row)
                self._rows.append(row)
        self.todo_layout.addStretch(1)

    def _accent(self) -> str:
        category = self.store.category(self.note.category_id)
        return category.color if category else "#7F9CFF"

    def _todo_toggled(self, item: TodoItem, checked: bool) -> None:
        self._mark_dirty()
        self._update_meta()

    def _todo_text(self, item: TodoItem, text: str) -> None:
        self._mark_dirty()

    def _add_todo_from_input(self) -> None:
        text = self.todo_input.text().strip()
        if not text:
            return
        item = TodoItem(uuid.uuid4().hex[:12], text)
        self.note.todos.append(item)
        self.todo_input.clear()
        self._rebuild_todos()
        self._rows[-1].focus_editor()
        self._mark_dirty()
        self._update_meta()

    def _add_todo_after(self, item: TodoItem) -> None:
        if not item.text.strip():
            return
        index = next((i for i, t in enumerate(self.note.todos) if t.id == item.id), -1)
        if index < 0:
            return
        fresh = TodoItem(uuid.uuid4().hex[:12], "")
        self.note.todos.insert(index + 1, fresh)
        self._rebuild_todos()
        for row in self._rows:
            if row.item.id == fresh.id:
                row.focus_editor()
                break
        self._mark_dirty()

    def _delete_todo(self, item: TodoItem) -> None:
        self.note.todos = [t for t in self.note.todos if t.id != item.id]
        self._rebuild_todos()
        self._mark_dirty()
        self._update_meta()

    def _convert_kind(self) -> None:
        if self.note.kind == KIND_TODO:
            body = "\n".join(t.text for t in self.note.todos if t.text.strip())
            self.note.kind = KIND_TEXT
            if body or not self.note.body:
                self.note.body = body
        else:
            lines = [line.strip() for line in self.note.body.splitlines() if line.strip()]
            self.note.todos = [TodoItem(uuid.uuid4().hex[:12], line) for line in lines]
            self.note.kind = KIND_TODO
            self.note.body = ""
        self.note.touch()
        self._apply_kind()
        self._mark_dirty()
        self._flush()
        self._update_meta()

    # ---------------------------------------------------------------category
    def refresh_category(self) -> None:
        category = self.store.category(self.note.category_id)
        token = (category.id, category.name, category.color)
        if getattr(self, "_category_token", None) == token:
            return
        self._category_token = token
        self._apply_category()

    def _apply_category(self) -> None:
        category = self.store.category(self.note.category_id)
        color = category.color if category else "#7F9CFF"
        name = category.name if category else "未分类"
        self._category_token = (category.id, category.name, category.color)
        self.chip.setText(f"  {name}")
        self.chip.setIcon(dot_icon(color, 8))
        self.card.set_base(note_color(self.palette, color))
        self.card.set_accent(QColor(color))
        for row in self._rows:
            row.check.accent = color
            row.check.update()

    def set_category(self, category_id: str) -> None:
        if category_id == self.note.category_id:
            return
        category = self.store.category(category_id)
        if category is None:
            return
        if category.kind != self.note.kind:
            if not self._confirm_kind_switch(category.kind):
                return
        self.note.category_id = category_id
        if category.kind != self.note.kind:
            self._convert_kind()
        self._apply_category()
        self._mark_dirty()
        self._flush()

    def _confirm_kind_switch(self, target_kind: str) -> bool:
        if target_kind == KIND_TODO:
            has_content = bool(self.note.body.strip())
            detail = "正文会按非空行拆成待办项，原来的段落格式不会保留。"
        else:
            has_content = any(item.text.strip() for item in self.note.todos)
            detail = "待办项会按行合并为正文，勾选状态不会保留。"
        if not has_content:
            return True
        return ConfirmDialog.ask(
            self,
            self.palette,
            "切换便签类型？",
            detail,
            "切换",
        )

    def _show_category_menu(self) -> None:
        menu = QMenu(self)
        for category in self.store.categories:
            selected = category.id == self.note.category_id
            text = f"{category.name}  ✓" if selected else category.name
            action = menu.addAction(dot_icon(category.color, 10), text)
            action.triggered.connect(
                lambda checked=False, cid=category.id: self.set_category(cid)
            )
        menu.addSeparator()
        manage = menu.addAction(make_icon("folder", self.palette.sub, 16), "管理便签类别…")
        manage.triggered.connect(self.categories_requested.emit)
        menu.exec(self.chip.mapToGlobal(QPoint(0, self.chip.height() + 4)))

    # ------------------------------------------------------------------- pin
    def _apply_pin(self) -> None:
        flags = self.windowFlags()
        if self.note.pinned:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        visible = self.isVisible()
        self.setWindowFlags(flags)
        self.pin_btn.set_visual(
            "pin" if self.note.pinned else "pin_off",
            self._accent() if self.note.pinned else self.palette.sub,
        )
        self.pin_btn.setToolTip("取消置顶" if self.note.pinned else "置顶窗口")
        if visible:
            self.show()

    def _toggle_pin(self) -> None:
        self.note.pinned = not self.note.pinned
        self._apply_pin()
        self._mark_dirty()
        self._flush()

    # ------------------------------------------------------------------ menus
    def _show_more_menu_at_button(self) -> None:
        self._show_more_menu(self.more_btn.mapToGlobal(QPoint(0, self.more_btn.height() + 4)))

    def _show_more_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        pin_text = "取消置顶" if self.note.pinned else "置顶窗口"
        pin_action = menu.addAction(pin_text)
        pin_action.triggered.connect(self._toggle_pin)

        convert_text = "转为文本便签" if self.note.kind == KIND_TODO else "转为待办清单"
        convert_action = menu.addAction(convert_text)
        convert_action.triggered.connect(self._convert_kind)

        new_action = menu.addAction(make_icon("plus", self.palette.sub, 16), "新建便签")
        new_action.triggered.connect(self.new_note_requested.emit)

        menu.addSeparator()
        delete_action = menu.addAction(make_icon("trash", "#F0736F", 16), "删除便签")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.note.id))
        menu.exec(position)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self._show_more_menu(event.globalPos())

    # --------------------------------------------------------------- geometry
    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        if self._geometry_ready:
            self._geom_timer.start()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._geometry_ready:
            self._geom_timer.start()

    def _save_geometry(self) -> None:
        if not self.isVisible():
            return
        rect = self.geometry()
        self.note.x, self.note.y = rect.x(), rect.y()
        self.note.width, self.note.height = rect.width(), rect.height()
        self.store.save()

    # ------------------------------------------------------------- visibility
    def show_note(self) -> None:
        self.note.open_window = True
        self.show()
        self.raise_()
        self.activateWindow()
        if not self._geometry_ready:
            self._geometry_ready = True
        self._flush()

    def hide_note(self) -> None:
        self._flush()
        self.note.open_window = False
        self.store.save()
        self.hide()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide_note()

    def refresh_theme(self, palette: Palette) -> None:
        self.palette = palette
        self.card.set_palette(palette)
        self._apply_category()
        self._apply_kind()
        self._update_meta()
