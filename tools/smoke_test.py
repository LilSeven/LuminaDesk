"""Visual smoke test: builds a few notes and screenshots the main surfaces."""
from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["LUMINA_DATA_DIR"] = tempfile.mkdtemp(prefix="lumina-visual-")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.application import LuminaApp  # noqa: E402
from app.category_dialog import CategoryDialog  # noqa: E402
from app.note_manager import NoteManager  # noqa: E402
from app.notes import KIND_TODO, TodoItem, _new_id  # noqa: E402
from app.settings import SettingsDialog  # noqa: E402

OUT = ROOT / "shots"
OUT.mkdir(exist_ok=True)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app.setStyle("Fusion")
controller = LuminaApp(app)

memo = controller.store.create_note("memo", title="周五之前")
memo.body = (
    "· 把发布说明补完，附上更新日志和截图\n"
    "· 给设计稿加一版深色方案\n"
    "· 问一下 Alex 下周的排期"
)
memo.touch()

todo = controller.store.create_note("todo", title="今天要做的事", kind=KIND_TODO)
todo.todos = [
    TodoItem(_new_id(), "整理桌面与窗口布局", True),
    TodoItem(_new_id(), "检查天气接口的缓存逻辑", False),
    TodoItem(_new_id(), "把便签配色换成暖色系", False),
    TodoItem(_new_id(), "导出第一版安装包", False),
]
todo.touch()
controller.store.save()

shot_widgets: list[tuple[str, int, int]] = []


def grab(widget, name: str) -> None:
    pixmap = widget.grab()
    ok = pixmap.save(str(OUT / name))
    print(f"grab {name}: visible={widget.isVisible()} size={widget.width()}x{widget.height()} ok={ok}", flush=True)
    shot_widgets.append((name, pixmap.width(), pixmap.height()))


def guarded(fn):
    def inner() -> None:
        try:
            fn()
        except Exception:
            traceback.print_exc()
            print("stage failed", fn.__name__, flush=True)
            finish()
    return inner


@guarded
def stage_one() -> None:
    print("stage one", flush=True)
    controller.open_note(memo.id)
    controller.open_note(todo.id)
    grab(controller.clock, "clock-dark.png")


@guarded
def stage_two() -> None:
    print("stage two", flush=True)
    for index, window in enumerate(controller._windows.values()):
        grab(window, f"note-{index}.png")
    settings = SettingsDialog(controller.clock, controller.palette, controller.cfg)
    settings.show()
    QTimer.singleShot(650, lambda: after_settings(settings))


def after_settings(settings) -> None:
    guarded(lambda: (grab(settings, "settings.png"), settings.close(), stage_three()))()


@guarded
def stage_three() -> None:
    print("stage three", flush=True)
    manager = NoteManager(controller.clock, controller.palette, controller.store)
    manager.setModal(False)
    manager.show()
    QTimer.singleShot(650, lambda: after_manager(manager))


def after_manager(manager) -> None:
    grab(manager, "manager.png")
    manager.close()
    stage_four()


@guarded
def stage_four() -> None:
    print("stage four", flush=True)
    categories = CategoryDialog(controller.clock, controller.palette, controller.store)
    categories.show()
    QTimer.singleShot(650, lambda: after_categories(categories))


def after_categories(categories) -> None:
    grab(categories, "categories.png")
    categories.close()
    finish()


def finish() -> None:
    for name, width, height in shot_widgets:
        print(f"{name} {width}x{height}", flush=True)
    controller.quit()


QTimer.singleShot(2400, stage_one)
QTimer.singleShot(3200, stage_two)
QTimer.singleShot(15000, finish)
sys.exit(app.exec())
