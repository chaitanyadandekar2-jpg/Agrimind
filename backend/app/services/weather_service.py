"""Weather service wrapper for Open-Meteo API.

Retrieves daily and hourly weather forecasts for agricultural decision support,
including spray window assessment, temperature, wind, humidity, and rainfall.
"""
from __future__ import annotations

import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List

OPEN_METEO_BASE_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")


class WeatherServiceError(Exception):
    pass


async def get_forecast(latitude: float, longitude: float, days: int = 5) -> dict:
    """Fetch daily + hourly forecast variables relevant to agricultural application timing.

    Returns:
    - raw: raw Open-Meteo payload
    - days: list of daily summary dictionaries
    - hourly_today: list of hourly forecast slots for the first day
    - windows: summary of morning (6-10), afternoon (11-15), evening (16-19) conditions
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join([
            "precipitation_sum",
            "precipitation_probability_max",
            "temperature_2m_max",
            "temperature_2m_min",
            "windspeed_10m_max",
            "relative_humidity_2m_max",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "windspeed_10m",
        ]),
        "forecast_days": days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPEN_METEO_BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(f"Weather provider request failed: {exc}") from exc

    data = resp.json()
    daily = data.get("daily", {})
    days_list = []
    dates = daily.get("time", [])
    for i, date in enumerate(dates):
        days_list.append({
            "date": date,
            "precipitation_mm": _safe_get(daily, "precipitation_sum", i),
            "precipitation_probability_pct": _safe_get(daily, "precipitation_probability_max", i),
            "temp_max_c": _safe_get(daily, "temperature_2m_max", i),
            "temp_min_c": _safe_get(daily, "temperature_2m_min", i),
            "wind_max_kmh": _safe_get(daily, "windspeed_10m_max", i),
            "humidity_max_pct": _safe_get(daily, "relative_humidity_2m_max", i),
        })

    # Process hourly data for Day 0 (today)
    hourly = data.get("hourly", {})
    hourly_today: List[Dict[str, Any]] = []
    hourly_times = hourly.get("time", [])

    # The first 24 slots correspond to day 0
    today_slot_count = min(24, len(hourly_times))
    for i in range(today_slot_count):
        t_str = hourly_times[i]
        hour = int(t_str.split("T")[-1].split(":")[0]) if "T" in t_str else i
        hourly_today.append({
            "time": t_str,
            "hour": hour,
            "temperature_c": _safe_get(hourly, "temperature_2m", i),
            "humidity_pct": _safe_get(hourly, "relative_humidity_2m", i),
            "precipitation_prob_pct": _safe_get(hourly, "precipitation_probability", i),
            "precipitation_mm": _safe_get(hourly, "precipitation", i),
            "wind_kmh": _safe_get(hourly, "windspeed_10m", i),
        })

    # Assess morning (6-10 AM) and evening (4-7 PM) conditions
    morning_slots = [h for h in hourly_today if 6 <= h["hour"] <= 10]
    evening_slots = [h for h in hourly_today if 16 <= h["hour"] <= 19]

    # Full daytime agricultural spray timeline: 06:00 to 17:00 (6 AM to 5 PM)
    spray_timeline = [
        assess_spray_hour(h)
        for h in hourly_today
        if 6 <= h["hour"] <= 17
    ]

    windows = {
        "morning": _summarize_window(morning_slots, "Morning (06:00 - 10:00)"),
        "evening": _summarize_window(evening_slots, "Evening (16:00 - 19:00)"),
    }

    return {
        "raw": data,
        "days": days_list,
        "hourly_today": hourly_today,
        "windows": windows,
        "spray_timeline": spray_timeline,
    }


def _safe_get(d: dict, key: str, idx: int):
    arr = d.get(key)
    if not arr or idx >= len(arr):
        return None
    return arr[idx]


def _summarize_window(slots: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    if not slots:
        return {"label": label, "status": "UNKNOWN", "detail": "Hourly forecast not available"}

    avg_temp = round(sum(s["temperature_c"] or 25 for s in slots) / len(slots), 1)
    max_wind = max((s["wind_kmh"] or 0 for s in slots), default=0)
    max_rain_prob = max((s["precipitation_prob_pct"] or 0 for s in slots), default=0)
    total_rain = sum((s["precipitation_mm"] or 0 for s in slots))

    # Agronomic spray rules for window:
    # Suitable if wind < 15 km/h, rain prob < 30%, temp < 32°C
    is_spray_safe = max_wind < 15.0 and max_rain_prob < 30 and avg_temp < 32.0 and total_rain < 0.5
    status = "GO" if is_spray_safe else "WAIT"

    reasons = []
    if max_wind >= 15.0:
        reasons.append(f"breezy wind ({max_wind} km/h, limit 15 km/h)")
    if max_rain_prob >= 30:
        reasons.append(f"rain probability ({max_rain_prob}%)")
    if avg_temp >= 32.0:
        reasons.append(f"high temperature ({avg_temp}°C)")

    detail = "Good spray conditions" if is_spray_safe else f"Sub-optimal due to {', '.join(reasons)}"
    return {
        "label": label,
        "status": status,
        "temp_avg_c": avg_temp,
        "wind_max_kmh": max_wind,
        "rain_prob_pct": max_rain_prob,
        "detail": detail,
    }


def assess_spray_hour(slot: Dict[str, Any]) -> Dict[str, Any]:
    hour = slot.get("hour", 0)
    temp = slot.get("temperature_c")
    if temp is None:
        temp = 25.0
    humidity = slot.get("humidity_pct")
    if humidity is None:
        humidity = 60
    rain_prob = slot.get("precipitation_prob_pct") or 0
    rain_mm = slot.get("precipitation_mm") or 0.0
    wind = slot.get("wind_kmh") or 0.0

    unsafe_reasons = []
    caution_reasons = []

    # Wind rules (spray drift)
    if wind >= 15.0:
        unsafe_reasons.append(f"High wind ({wind} km/h) causes spray drift")
    elif wind >= 12.0:
        caution_reasons.append(f"Moderate breeze ({wind} km/h) requires drift-reduction nozzles")

    # Temperature rules (evaporation & scorch)
    if temp >= 32.0:
        unsafe_reasons.append(f"High heat ({temp}°C) causes leaf scorch & evaporation")
    elif temp >= 30.0:
        caution_reasons.append(f"Elevated temperature ({temp}°C) accelerates drying")

    # Rain rules (wash-off)
    if rain_mm >= 0.5 or rain_prob >= 40:
        unsafe_reasons.append(f"Rain risk ({rain_prob}%, {rain_mm}mm) washes off spray")
    elif rain_prob >= 25:
        caution_reasons.append(f"Moderate rain probability ({rain_prob}%)")

    # Humidity rules
    if humidity < 35:
        caution_reasons.append(f"Low humidity ({humidity}%) reduces droplet uptake")

    if unsafe_reasons:
        status = "AVOID"
        summary = "Unfavorable: " + "; ".join(unsafe_reasons)
    elif caution_reasons:
        status = "CAUTION"
        summary = "Caution: " + "; ".join(caution_reasons)
    else:
        status = "GO"
        summary = "Optimal conditions: good droplet coverage and leaf absorption."

    display_ampm = f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}"

    return {
        "hour": hour,
        "time_label": f"{hour:02d}:00",
        "display_time": display_ampm,
        "status": status,  # "GO" | "CAUTION" | "AVOID"
        "temperature_c": temp,
        "humidity_pct": humidity,
        "precipitation_prob_pct": rain_prob,
        "precipitation_mm": rain_mm,
        "wind_kmh": wind,
        "reasons": unsafe_reasons or caution_reasons or ["Ideal spray window"],
        "summary": summary,
    }


async def geocode_location(name: str) -> tuple[float, float] | None:
    """Resolve a free-text location to latitude and longitude."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params={"name": name, "count": 1})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(f"Geocoding request failed: {exc}") from exc

    results = resp.json().get("results")
    if not results:
        return None
    top = results[0]
    return float(top["latitude"]), float(top["longitude"])
