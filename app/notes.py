"""Sticky-note data model and JSON persistence.

Categories are fully user editable: name, colour and default note kind
(``text`` or ``todo``).  A note keeps its own kind so switching category
never silently rewrites its content.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal

from .paths import data_dir


KIND_TEXT = "text"
KIND_TODO = "todo"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Category:
    id: str
    name: str
    color: str
    kind: str = KIND_TEXT

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color, "kind": self.kind}

    @classmethod
    def from_dict(cls, raw: dict) -> "Category | None":
        try:
            cid = str(raw["id"])
            name = str(raw["name"]).strip()
            color = str(raw.get("color", "#7F9CFF"))
            kind = raw.get("kind", KIND_TEXT)
            if not cid or not name:
                return None
            if kind not in (KIND_TEXT, KIND_TODO):
                kind = KIND_TEXT
            return cls(cid, name, color, kind)
        except (KeyError, TypeError, ValueError):
            return None


DEFAULT_CATEGORIES: list[Category] = [
    Category("memo", "备忘录", "#F2C879", KIND_TEXT),
    Category("todo", "待办列表", "#7F9CFF", KIND_TODO),
    Category("idea", "灵感", "#C3A6FF", KIND_TEXT),
    Category("inbox", "收集箱", "#7ED6C1", KIND_TEXT),
]


@dataclass
class TodoItem:
    id: str
    text: str
    done: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "done": self.done}

    @classmethod
    def from_dict(cls, raw: dict) -> "TodoItem | None":
        try:
            text = str(raw.get("text", "")).strip()
            if not text:
                return None
            return cls(str(raw.get("id") or _new_id()), text, bool(raw.get("done", False)))
        except (TypeError, ValueError):
            return None


@dataclass
class Note:
    id: str
    title: str
    category_id: str
    kind: str
    body: str = ""
    todos: list[TodoItem] = field(default_factory=list)
    pinned: bool = False
    open_window: bool = False
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def progress(self) -> tuple[int, int]:
        total = len(self.todos)
        done = sum(1 for item in self.todos if item.done)
        return done, total

    def preview(self, limit: int = 72) -> str:
        if self.kind == KIND_TODO:
            if not self.todos:
                return "空待办清单"
            done, total = self.progress()
            first_open = next((t.text for t in self.todos if not t.done), "")
            head = f"{done}/{total} 已完成"
            return f"{head} · {first_open}" if first_open else head
        text = " ".join(line.strip() for line in self.body.splitlines() if line.strip())
        return text[:limit] if text else "空便签"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category_id": self.category_id,
            "kind": self.kind,
            "body": self.body,
            "todos": [t.to_dict() for t in self.todos],
            "pinned": self.pinned,
            "open_window": self.open_window,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Note | None":
        try:
            nid = str(raw["id"])
            kind = raw.get("kind", KIND_TEXT)
            if kind not in (KIND_TEXT, KIND_TODO):
                kind = KIND_TEXT
            todos = [
                item
                for item in (TodoItem.from_dict(t) for t in raw.get("todos") or [])
                if item is not None
            ]
            return cls(
                id=nid,
                title=str(raw.get("title", "")),
                category_id=str(raw.get("category_id", "memo")),
                kind=kind,
                body=str(raw.get("body", "")),
                todos=todos,
                pinned=bool(raw.get("pinned", False)),
                open_window=bool(raw.get("open_window", False)),
                x=raw.get("x"),
                y=raw.get("y"),
                width=raw.get("width"),
                height=raw.get("height"),
                created_at=str(raw.get("created_at") or _now()),
                updated_at=str(raw.get("updated_at") or _now()),
            )
        except (KeyError, TypeError, ValueError):
            return None


class NoteStore(QObject):
    """In-memory collection with atomic, immediate persistence."""

    changed = Signal()

    def __init__(self, path: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.path = path or (data_dir() / "notes.json")
        self.categories: list[Category] = [Category(**c.to_dict()) for c in DEFAULT_CATEGORIES]
        self.notes: list[Note] = []
        self._loading = False
        self.load()

    # ---------------------------------------------------------------- storage
    def load(self) -> None:
        self._loading = True
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._loading = False
            return

        if isinstance(raw, dict):
            categories = [
                cat
                for cat in (Category.from_dict(c) for c in raw.get("categories") or [])
                if cat is not None
            ]
            if categories:
                self.categories = categories
            notes = [
                note
                for note in (Note.from_dict(n) for n in raw.get("notes") or [])
                if note is not None
            ]
            self.notes = notes
        self._ensure_categories()
        self._loading = False

    def save(self) -> None:
        if self._loading:
            return
        payload = {
            "version": 1,
            "categories": [c.to_dict() for c in self.categories],
            "notes": [n.to_dict() for n in self.sorted_notes()],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            return
        self.changed.emit()

    def _ensure_categories(self) -> None:
        if not self.categories:
            self.categories = [Category(**c.to_dict()) for c in DEFAULT_CATEGORIES]
        known = {c.id for c in self.categories}
        for note in self.notes:
            if note.category_id not in known:
                note.category_id = self.categories[0].id

    # ------------------------------------------------------------------ notes
    def sorted_notes(self) -> list[Note]:
        return sorted(self.notes, key=lambda n: (0 if n.pinned else 1, _neg_time(n.updated_at)))

    def ordered(self) -> list[Note]:
        """Pinned first, then most recently updated."""
        return self.sorted_notes()

    def get(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.id == note_id), None)

    def category(self, category_id: str) -> Category:
        return next((c for c in self.categories if c.id == category_id), self.categories[0])

    def create_note(self, category_id: str | None = None, kind: str | None = None,
                     title: str = "") -> Note:
        category = self.category(category_id) if category_id else self.categories[0]
        note = Note(
            id=_new_id(),
            title=title,
            category_id=category.id,
            kind=kind or category.kind,
        )
        self.notes.append(note)
        self.save()
        return note

    def remove_note(self, note_id: str) -> None:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        if len(self.notes) != before:
            self.save()

    def count(self) -> int:
        return len(self.notes)

    # ------------------------------------------------------------- categories
    def add_category(self, name: str, color: str, kind: str = KIND_TEXT) -> Category | None:
        name = name.strip()
        if not name:
            return None
        category = Category(_new_id(), name[:24], color, kind if kind in (KIND_TEXT, KIND_TODO) else KIND_TEXT)
        self.categories.append(category)
        self.save()
        return category

    def update_category(self, category_id: str, *, name: str | None = None,
                        color: str | None = None, kind: str | None = None) -> None:
        category = next((c for c in self.categories if c.id == category_id), None)
        if category is None:
            return
        if name is not None and name.strip():
            category.name = name.strip()[:24]
        if color:
            category.color = color
        if kind in (KIND_TEXT, KIND_TODO):
            category.kind = kind
        self.save()

    def delete_category(self, category_id: str) -> bool:
        if len(self.categories) <= 1:
            return False
        category = next((c for c in self.categories if c.id == category_id), None)
        if category is None:
            return False
        fallback = next(c for c in self.categories if c.id != category_id)
        for note in self.notes:
            if note.category_id == category_id:
                note.category_id = fallback.id
        self.categories = [c for c in self.categories if c.id != category_id]
        self.save()
        return True


def _neg_time(stamp: str) -> float:
    """Sort helper: turn an ISO timestamp into a descending-friendly key."""
    try:
        return -datetime.fromisoformat(stamp).timestamp()
    except ValueError:
        return 0.0


def update_todos(note: Note, items: Iterable[tuple[str, bool]]) -> None:
    """Replace todo items while preserving ids for entries with the same text."""
    old = {item.text: item for item in note.todos}
    rebuilt: list[TodoItem] = []
    for text, done in items:
        text = text.strip()
        if not text:
            continue
        previous = old.get(text)
        rebuilt.append(TodoItem(previous.id if previous else _new_id(), text, done))
    note.todos = rebuilt
