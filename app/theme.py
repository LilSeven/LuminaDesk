"""Theme palettes and the application-wide stylesheet."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


def _rgb(hex_color: str) -> tuple[int, int, int]:
    color = QColor(hex_color)
    return color.red(), color.green(), color.blue()


def mix_hex(color_a: str | QColor | tuple[int, int, int],
            color_b: str | QColor | tuple[int, int, int], ratio: float) -> QColor:
    """Blend two colours; ratio is the weight of ``color_b``."""
    def as_color(value: str | QColor | tuple[int, int, int]) -> QColor:
        if isinstance(value, QColor):
            return value
        if isinstance(value, tuple):
            return QColor(*value)
        return QColor(value)

    a = as_color(color_a)
    b = as_color(color_b)
    ratio = max(0.0, min(1.0, ratio))
    return QColor(
        round(a.red() * (1 - ratio) + b.red() * ratio),
        round(a.green() * (1 - ratio) + b.green() * ratio),
        round(a.blue() * (1 - ratio) + b.blue() * ratio),
    )


def rgba(color: str | QColor | tuple[int, int, int], alpha: int | float) -> str:
    """CSS rgba() string; alpha may be 0-1 (fraction) or 0-255 (byte)."""
    if isinstance(color, QColor):
        c = color
    elif isinstance(color, tuple):
        c = QColor(*color)
    else:
        c = QColor(color)
    value = float(alpha)
    byte = round(value * 255) if value <= 1.0 else round(value)
    return f"rgba({c.red()},{c.green()},{c.blue()},{max(0, min(255, byte))})"


@dataclass(frozen=True)
class Palette:
    name: str
    dark: bool
    card: tuple[int, int, int]
    dialog: tuple[int, int, int]
    note: tuple[int, int, int]
    text: str
    sub: str
    faint: str
    border: str
    field: str
    hover: str
    shadow_alpha: int
    accent_text: str = "#10131A"


DARK = Palette(
    name="dark",
    dark=True,
    card=(22, 25, 34),
    dialog=(24, 27, 37),
    note=(25, 28, 38),
    text="#F3F5F9",
    sub="#A4ADBC",
    faint="#6E7787",
    border="rgba(255,255,255,0.09)",
    field="rgba(255,255,255,0.07)",
    hover="rgba(255,255,255,0.12)",
    shadow_alpha=170,
    accent_text="#0D1016",
)

LIGHT = Palette(
    name="light",
    dark=False,
    card=(250, 251, 253),
    dialog=(255, 255, 255),
    note=(255, 255, 255),
    text="#1B2029",
    sub="#5B6575",
    faint="#8B94A3",
    border="rgba(20,28,42,0.10)",
    field="rgba(20,28,42,0.05)",
    hover="rgba(20,28,42,0.09)",
    shadow_alpha=70,
    accent_text="#10131A",
)


def palette_for(name: str) -> Palette:
    return LIGHT if name == "light" else DARK


def accent_text_color(accent: str) -> str:
    color = QColor(accent)
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return "#10131A" if luminance > 0.55 else "#FFFFFF"


def note_color(palette: Palette, category_color: str) -> QColor:
    """Tinted card colour for a sticky note."""
    ratio = 0.14 if palette.dark else 0.20
    base = QColor(*palette.note)
    tinted = mix_hex(base, category_color, ratio)
    if palette.dark:
        tinted = mix_hex(tinted, "#0B0D12", 0.18)
    return tinted


def build_qss(palette: Palette, accent: str) -> str:
    p = palette
    accent_text = accent_text_color(accent)
    accent_soft = rgba(accent, 0.18 if p.dark else 0.13)
    accent_hover = mix_hex(accent, "#FFFFFF" if p.dark else "#000000", 0.12).name()
    scroll = rgba(p.text, 0.16)
    scroll_hover = rgba(p.text, 0.28)
    menu_bg = rgba(p.dialog, 0.98)
    return f"""
    QWidget {{
        font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif;
        font-size: 13px;
        color: {p.text};
    }}
    QDialog, QMessageBox {{ background: transparent; }}
    QLabel {{ background: transparent; }}
    QLabel#sub {{ color: {p.sub}; }}
    QLabel#faint {{ color: {p.faint}; font-size: 12px; }}
    QLabel#section {{
        color: {p.sub}; font-size: 11px; font-weight: 600; letter-spacing: 1px;
    }}
    QLabel#noteMeta {{ color: {p.faint}; font-size: 11px; }}
    QLabel#emptyHint {{ color: {p.faint}; font-size: 12px; padding: 8px 0; }}
    QLabel#noteTitle {{ font-size: 14px; font-weight: 600; color: {p.text}; }}
    QLabel#notePreview {{ color: {p.sub}; font-size: 12px; }}
    QFrame#noteRow {{
        background: {p.field}; border: 1px solid {p.border}; border-radius: 12px;
    }}
    QFrame#noteRow:hover {{ background: {p.hover}; }}
    QLabel#dialogTitle {{ font-size: 17px; font-weight: 600; color: {p.text}; }}
    QLabel#rowTitle {{ font-size: 14px; font-weight: 600; color: {p.text}; }}
    QWidget#transparent {{ background: transparent; }}

    QPushButton {{
        background: {p.field}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 9px;
        padding: 6px 13px;
    }}
    QPushButton:hover {{ background: {p.hover}; }}
    QPushButton:pressed {{ background: {accent_soft}; }}
    QPushButton:disabled {{ color: {p.faint}; }}
    QPushButton#accent {{
        background: {accent}; color: {accent_text};
        border: none; font-weight: 600;
    }}
    QPushButton#accent:hover {{ background: {accent_hover}; }}
    QPushButton#ghost {{
        background: transparent; border: none; color: {p.sub}; padding: 4px 8px;
    }}
    QPushButton#ghost:hover {{ color: {p.text}; background: {p.field}; }}
    QPushButton#danger {{
        background: transparent; border: none; color: #F0736F; padding: 4px 8px;
    }}
    QPushButton#danger:hover {{ background: rgba(240,115,111,0.12); }}
    QPushButton#seg {{
        background: transparent; border: 1px solid transparent;
        border-radius: 8px; padding: 6px 16px; color: {p.sub};
    }}
    QPushButton#seg:hover {{ color: {p.text}; }}
    QPushButton#seg:checked {{
        background: {accent_soft}; border-color: {rgba(accent, 0.55)};
        color: {p.text}; font-weight: 600;
    }}
    QPushButton#chip {{
        background: {p.field}; border: 1px solid {p.border};
        border-radius: 10px; padding: 3px 9px; font-size: 12px; color: {p.sub};
    }}
    QPushButton#chip:hover {{ background: {p.hover}; color: {p.text}; }}

    QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 4px; }}
    QToolButton:hover {{ background: {p.field}; }}
    QToolButton:pressed {{ background: {p.hover}; }}

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {p.field}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 8px;
        padding: 7px 9px;
        selection-background-color: {accent}; selection-color: {accent_text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QComboBox:focus, QSpinBox:focus {{ border-color: {rgba(accent, 0.75)}; }}
    QLineEdit#flat {{
        background: transparent; border: none; padding: 0;
    }}
    QLineEdit#titleEdit {{
        background: transparent; border: none; padding: 0;
        font-size: 15px; font-weight: 600;
    }}
    QTextEdit#noteBody {{
        background: transparent; border: none; padding: 0;
        font-size: 13px; line-height: 150%;
    }}
    QLineEdit#todoEdit {{
        background: transparent; border: none; padding: 2px 0; font-size: 13px;
    }}
    QLineEdit#todoEdit:focus {{ border: none; }}
    QLineEdit#addTodo {{
        background: transparent; border: none; padding: 4px 0;
        color: {p.sub}; font-size: 12px;
    }}
    QLineEdit#addTodo:focus {{ color: {p.text}; border: none; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {menu_bg}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 8px; padding: 4px;
        selection-background-color: {accent_soft}; selection-color: {p.text};
        outline: none;
    }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
    QScrollBar::handle:vertical {{
        background: {scroll}; border-radius: 3px; min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
    QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 2px; }}
    QScrollBar::handle:horizontal {{
        background: {scroll}; border-radius: 3px; min-width: 24px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QMenu {{
        background: {menu_bg}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 10px; padding: 6px;
    }}
    QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {p.field}; }}
    QMenu::item:disabled {{ color: {p.faint}; }}
    QMenu::separator {{ height: 1px; background: {p.border}; margin: 5px 8px; }}
    QMenu::indicator {{ width: 14px; height: 14px; }}

    QSlider::groove:horizontal {{
        height: 4px; background: {p.field}; border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
    QSlider::handle:horizontal {{
        background: #FFFFFF; width: 14px; height: 14px;
        margin: -5px 0; border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{ background: {accent_hover}; }}

    QCheckBox {{ background: transparent; spacing: 8px; }}
    QSizeGrip {{ background: transparent; width: 14px; height: 14px; }}

    QToolTip {{
        background: {menu_bg}; color: {p.text};
        border: 1px solid {p.border}; padding: 5px 8px; border-radius: 6px;
    }}
    """
