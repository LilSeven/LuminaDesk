"""Weather data via Open-Meteo (free, no API key required)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, QUrl, QUrlQuery, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from .paths import VERSION, data_dir

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# WMO weather interpretation codes -> (Chinese label, icon kind)
WMO: dict[int, tuple[str, str]] = {
    0: ("晴朗", "sun"),
    1: ("晴间少云", "sun"),
    2: ("多云", "cloud-sun"),
    3: ("阴天", "cloud"),
    45: ("有雾", "fog"),
    48: ("雾凇", "fog"),
    51: ("小毛毛雨", "drizzle"),
    53: ("毛毛雨", "drizzle"),
    55: ("浓毛毛雨", "drizzle"),
    56: ("冻毛毛雨", "sleet"),
    57: ("强冻毛毛雨", "sleet"),
    61: ("小雨", "rain"),
    63: ("中雨", "rain"),
    65: ("大雨", "rain"),
    66: ("冻雨", "sleet"),
    67: ("强冻雨", "sleet"),
    71: ("小雪", "snow"),
    73: ("中雪", "snow"),
    75: ("大雪", "snow"),
    77: ("米雪", "snow"),
    80: ("阵雨", "rain"),
    81: ("强阵雨", "rain"),
    82: ("暴雨", "rain"),
    85: ("阵雪", "snow"),
    86: ("强阵雪", "snow"),
    95: ("雷阵雨", "thunder"),
    96: ("雷阵雨伴冰雹", "thunder"),
    99: ("强雷暴伴冰雹", "thunder"),
}


def describe(code: int) -> tuple[str, str]:
    return WMO.get(int(code), ("未知天气", "cloud"))


@dataclass
class Weather:
    city: str
    temp: float
    feels: float
    humidity: int
    wind: float
    code: int
    is_day: bool
    tmax: float
    tmin: float
    sunrise: str
    sunset: str
    fetched_at: str

    @property
    def description(self) -> str:
        return describe(self.code)[0]

    @property
    def icon(self) -> str:
        kind = describe(self.code)[1]
        if kind == "sun" and not self.is_day:
            return "moon"
        if kind == "cloud-sun" and not self.is_day:
            return "cloud-moon"
        return kind

    @property
    def fetched_label(self) -> str:
        try:
            return datetime.fromisoformat(self.fetched_at).strftime("%H:%M")
        except ValueError:
            return "--:--"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Weather | None":
        try:
            return cls(
                city=str(raw["city"]),
                temp=float(raw["temp"]),
                feels=float(raw["feels"]),
                humidity=int(raw["humidity"]),
                wind=float(raw["wind"]),
                code=int(raw["code"]),
                is_day=bool(raw["is_day"]),
                tmax=float(raw["tmax"]),
                tmin=float(raw["tmin"]),
                sunrise=str(raw.get("sunrise", "")),
                sunset=str(raw.get("sunset", "")),
                fetched_at=str(raw["fetched_at"]),
            )
        except (KeyError, TypeError, ValueError):
            return None


class WeatherService(QObject):
    updated = Signal(object)       # Weather
    failed = Signal(str)
    cities = Signal(object)        # list[dict]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._pending = False
        self._city_reply = None
        self._cache_path = data_dir() / "weather_cache.json"

    # ------------------------------------------------------------------ fetch
    def refresh(self, city: str, latitude: float, longitude: float) -> None:
        if self._pending:
            return
        self._pending = True

        query = QUrlQuery()
        query.addQueryItem("latitude", f"{latitude:.4f}")
        query.addQueryItem("longitude", f"{longitude:.4f}")
        query.addQueryItem(
            "current",
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m",
        )
        query.addQueryItem("daily", "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset")
        query.addQueryItem("timezone", "auto")
        query.addQueryItem("forecast_days", "1")

        url = QUrl(FORECAST_URL)
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setTransferTimeout(15000)
        request.setHeader(QNetworkRequest.UserAgentHeader, f"LuminaDesk/{VERSION}")
        reply = self._nam.get(request)
        reply.finished.connect(lambda: self._on_weather(reply, city))

    def _on_weather(self, reply, city: str) -> None:
        self._pending = False
        try:
            if reply.error() != reply.NetworkError.NoError:
                self.failed.emit(reply.errorString() or "网络请求失败")
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            current = payload["current"]
            daily = payload["daily"]
            weather = Weather(
                city=city,
                temp=float(current["temperature_2m"]),
                feels=float(current["apparent_temperature"]),
                humidity=int(current["relative_humidity_2m"]),
                wind=float(current["wind_speed_10m"]),
                code=int(current["weather_code"]),
                is_day=bool(current["is_day"]),
                tmax=float(daily["temperature_2m_max"][0]),
                tmin=float(daily["temperature_2m_min"][0]),
                sunrise=_clock(daily.get("sunrise", [""])[0]),
                sunset=_clock(daily.get("sunset", [""])[0]),
                fetched_at=datetime.now().isoformat(timespec="seconds"),
            )
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError):
            self.failed.emit("天气数据解析失败")
            return
        finally:
            reply.deleteLater()

        self._save_cache(weather)
        self.updated.emit(weather)

    # ------------------------------------------------------------------ cache
    def load_cache(self, city: str) -> Weather | None:
        try:
            raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        weather = Weather.from_dict(raw) if isinstance(raw, dict) else None
        if weather and weather.city == city:
            return weather
        return None

    def _save_cache(self, weather: Weather) -> None:
        try:
            self._cache_path.write_text(
                json.dumps(weather.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    # --------------------------------------------------------------- geocoding
    def search_city(self, name: str) -> None:
        name = name.strip()
        if not name:
            self.cities.emit([])
            return
        query = QUrlQuery()
        query.addQueryItem("name", name)
        query.addQueryItem("count", "8")
        query.addQueryItem("language", "zh")
        query.addQueryItem("format", "json")
        url = QUrl(GEOCODE_URL)
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setTransferTimeout(15000)
        request.setHeader(QNetworkRequest.UserAgentHeader, f"LuminaDesk/{VERSION}")
        reply = self._nam.get(request)
        self._city_reply = reply
        reply.finished.connect(lambda: self._on_cities(reply))

    def _on_cities(self, reply) -> None:
        results: list[dict[str, Any]] = []
        try:
            if reply.error() == reply.NetworkError.NoError:
                payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
                for item in payload.get("results") or []:
                    results.append(
                        {
                            "name": str(item.get("name", "")),
                            "admin1": str(item.get("admin1") or ""),
                            "country": str(item.get("country") or ""),
                            "latitude": float(item.get("latitude")),
                            "longitude": float(item.get("longitude")),
                            "timezone": str(item.get("timezone") or "auto"),
                        }
                    )
        except (ValueError, TypeError, UnicodeDecodeError):
            results = []
        finally:
            reply.deleteLater()
        self.cities.emit(results)


def _clock(stamp: str) -> str:
    """'2026-10-25T06:12' -> '06:12'."""
    if "T" in stamp:
        return stamp.split("T", 1)[1][:5]
    return stamp[:5]
