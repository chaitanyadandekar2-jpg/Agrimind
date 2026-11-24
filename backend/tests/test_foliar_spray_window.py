"""Tests for foliar spray vs soil application window evaluation."""
import pytest
from app.engine.application_window import assess_application_window


def test_foliar_spray_wind_threshold():
    # 18 km/h wind is safe for soil application (<30 km/h) but unsafe for foliar spray (<15 km/h)
    days = [
        {"date": "2026-08-27", "precipitation_mm": 0, "precipitation_probability_pct": 10, "wind_max_kmh": 18},
        {"date": "2026-08-28", "precipitation_mm": 0, "precipitation_probability_pct": 5, "wind_max_kmh": 10},
    ]

    soil_app = assess_application_window(days, needs_application=True, application_type="soil")
    assert soil_app.apply_today == "GO"

    foliar_app = assess_application_window(days, needs_application=True, application_type="foliar")
    assert foliar_app.apply_today == "WAIT"
    assert "spray drift" in foliar_app.reason.lower()
    assert foliar_app.next_window == "2026-08-28"


def test_foliar_spray_rain_washoff():
    # 45% rain probability triggers wash-off risk for foliar spray
    days = [
        {"date": "2026-08-27", "precipitation_mm": 2, "precipitation_probability_pct": 50, "wind_max_kmh": 10},
        {"date": "2026-08-28", "precipitation_mm": 0, "precipitation_probability_pct": 5, "wind_max_kmh": 10},
    ]

    foliar_app = assess_application_window(days, needs_application=True, application_type="foliar")
    assert foliar_app.apply_today == "WAIT"
    assert "wash-off" in foliar_app.reason.lower()


def test_hourly_morning_evening_window_guidance():
    days = [
        {"date": "2026-08-27", "precipitation_mm": 0, "precipitation_probability_pct": 5, "wind_max_kmh": 10},
    ]
    hourly_windows = {
        "morning": {"status": "GO", "detail": "Good spray conditions"},
        "evening": {"status": "GO", "detail": "Good spray conditions"},
    }

    result = assess_application_window(days, needs_application=True, windows_hourly=hourly_windows)
    assert result.apply_today == "GO"
    assert "morning" in result.reason.lower()
    assert "evening" in result.reason.lower()


def test_assess_spray_hour_rules():
    from app.services.weather_service import assess_spray_hour

    # 1. Safe condition at 7 AM
    safe_slot = {
        "hour": 7,
        "temperature_c": 24.0,
        "humidity_pct": 65,
        "precipitation_prob_pct": 5,
        "precipitation_mm": 0.0,
        "wind_kmh": 8.0,
    }
    safe_res = assess_spray_hour(safe_slot)
    assert safe_res["status"] == "GO"
    assert safe_res["hour"] == 7
    assert safe_res["time_label"] == "07:00"
    assert safe_res["display_time"] == "7:00 AM"

    # 2. Avoid condition at 13:00 (1 PM) due to extreme heat (34°C)
    hot_slot = {
        "hour": 13,
        "temperature_c": 34.5,
        "humidity_pct": 30,
        "precipitation_prob_pct": 0,
        "precipitation_mm": 0.0,
        "wind_kmh": 9.0,
    }
    hot_res = assess_spray_hour(hot_slot)
    assert hot_res["status"] == "AVOID"
    assert any("heat" in r.lower() or "scorch" in r.lower() for r in hot_res["reasons"])

    # 3. Avoid condition due to high wind (18 km/h)
    wind_slot = {
        "hour": 15,
        "temperature_c": 28.0,
        "humidity_pct": 50,
        "precipitation_prob_pct": 10,
        "precipitation_mm": 0.0,
        "wind_kmh": 18.0,
    }
    wind_res = assess_spray_hour(wind_slot)
    assert wind_res["status"] == "AVOID"
    assert any("drift" in r.lower() for r in wind_res["reasons"])

    # 4. Caution condition due to borderline wind (13 km/h)
    caution_slot = {
        "hour": 10,
        "temperature_c": 29.0,
        "humidity_pct": 55,
        "precipitation_prob_pct": 10,
        "precipitation_mm": 0.0,
        "wind_kmh": 13.0,
    }
    caution_res = assess_spray_hour(caution_slot)
    assert caution_res["status"] == "CAUTION"


def test_application_window_preserves_hourly_windows():
    days = [{"date": "2026-08-27", "precipitation_mm": 0, "precipitation_probability_pct": 5, "wind_max_kmh": 10}]
    sample_timeline = [
        {"hour": h, "time_label": f"{h:02d}:00", "status": "GO"}
        for h in range(6, 18)
    ]
    result = assess_application_window(days, needs_application=True, hourly_windows=sample_timeline)
    assert result.hourly_windows is not None
    assert len(result.hourly_windows) == 12
    assert result.hourly_windows[0]["hour"] == 6
    assert result.hourly_windows[-1]["hour"] == 17
