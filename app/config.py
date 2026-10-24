"""User preferences, persisted as JSON with defensive defaults."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .paths import data_dir


ACCENTS = ["#7F9CFF", "#7ED6C1", "#F5A97F", "#F08BB4", "#C3A6FF", "#F2C879"]


@dataclass
class Config:
    city_name: str = "上海"
    latitude: float = 31.2304
    longitude: float = 121.4737
    timezone: str = "Asia/Shanghai"

    transparency: int = 82          # 0-100, background opacity of the clock card
    theme: str = "dark"             # dark | light
    accent: str = "#7F9CFF"

    always_on_top: bool = True
    autostart: bool = False
    use_24h: bool = True
    show_seconds: bool = True
    show_lunar: bool = True

    refresh_minutes: int = 15
    window_x: int = -1
    window_y: int = -1
    notes_on_start: bool = False

    version: int = 1

    def __post_init__(self) -> None:
        self.normalize()

    def normalize(self) -> None:
        self.transparency = max(0, min(100, int(self.transparency)))
        if self.theme not in ("dark", "light"):
            self.theme = "dark"
        if self.accent not in ACCENTS:
            self.accent = ACCENTS[0]
        if self.refresh_minutes not in (5, 10, 15, 30, 60):
            self.refresh_minutes = 15
        self.latitude = float(self.latitude)
        self.longitude = float(self.longitude)
        self.refresh_minutes = int(self.refresh_minutes)
        self.use_24h = bool(self.use_24h)
        self.show_seconds = bool(self.show_seconds)
        self.show_lunar = bool(self.show_lunar)
        self.always_on_top = bool(self.always_on_top)
        self.autostart = bool(self.autostart)
        self.notes_on_start = bool(self.notes_on_start)
        self.window_x = int(self.window_x)
        self.window_y = int(self.window_y)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or (data_dir() / "config.json")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root must be an object")
            known = {f for f in cls.__dataclass_fields__}
            clean = {k: v for k, v in raw.items() if k in known}
            return cls(**clean)
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        path = path or (data_dir() / "config.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
