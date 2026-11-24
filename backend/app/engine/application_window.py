"""Agricultural application timing evaluator.

Determines WHEN recommended fertilizer/amendment applications should occur
based on live meteorological parameters. Pure deterministic rules; no LLM.

Rules:
1. Soil Application (e.g. Urea, SSP, MOP, Gypsum):
   - Heavy rain (>=20mm or >=70% probability) -> WAIT (nutrient leaching / runoff risk)
   - Otherwise -> GO today
2. Foliar Spray Application (e.g. ZnSO4, FeSO4, micronutrient sprays):
   - Wind speed >= 15-20 km/h -> WAIT (spray drift risk)
   - High rain probability (>=40%) -> WAIT (foliar wash-off)
   - Extreme daytime heat (>=32-35°C) -> recommend Morning (06:00-10:00) or Evening (16:00-19:00)
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from app.models.recommendation import ApplicationWindow

RAIN_MM_THRESHOLD = 20.0
RAIN_PROB_THRESHOLD = 70.0
WIND_KMH_THRESHOLD = 30.0

# Stricter thresholds for foliar spraying
FOLIAR_WIND_THRESHOLD = 15.0
FOLIAR_RAIN_PROB_THRESHOLD = 40.0


def assess_application_window(
    forecast_days: list[dict],
    needs_application: bool,
    application_type: str = "general",
    windows_hourly: Optional[Dict[str, Any]] = None,
    hourly_windows: Optional[List[Dict[str, Any]]] = None,
) -> ApplicationWindow:
    if not needs_application:
        return ApplicationWindow(
            recommendation="NO",
            apply_today="WAIT",
            reason="No active fertilizer/amendment application was recommended for the current soil status.",
            application_type=application_type,
            hourly_windows=hourly_windows,
        )

    if not forecast_days:
        return ApplicationWindow(
            recommendation="YES",
            apply_today="WAIT",
            reason="Weather forecast unavailable; cannot confirm a safe application window.",
            application_type=application_type,
            hourly_windows=hourly_windows,
        )

    today = forecast_days[0]
    rain = today.get("precipitation_mm") or 0
    rain_prob = today.get("precipitation_probability_pct") or 0
    wind = today.get("wind_max_kmh") or 0

    morning_info = windows_hourly.get("morning", {}).get("detail") if windows_hourly else None
    evening_info = windows_hourly.get("evening", {}).get("detail") if windows_hourly else None

    # Rain check (applies to all applications)
    if rain >= RAIN_MM_THRESHOLD or rain_prob >= RAIN_PROB_THRESHOLD:
        next_window = _find_next_clear_day(forecast_days[1:], application_type=application_type)
        if rain >= RAIN_MM_THRESHOLD:
            reason = f"Heavy rain expected today ({rain}mm) - risk of nutrient runoff."
        else:
            reason = f"High chance of rain today ({rain_prob}% probability, {rain}mm expected) - risk of nutrient runoff."

        return ApplicationWindow(
            recommendation="YES",
            apply_today="WAIT",
            reason=reason,
            next_window=next_window,
            forecast_summary=today,
            application_type=application_type,
            morning_window=morning_info,
            evening_window=evening_info,
            hourly_windows=hourly_windows,
        )

    # Foliar spray specific checks
    if application_type == "foliar":
        if wind >= FOLIAR_WIND_THRESHOLD:
            next_window = _find_next_clear_day(forecast_days[1:], application_type="foliar")
            return ApplicationWindow(
                recommendation="YES",
                apply_today="WAIT",
                reason=f"Wind speed today ({wind} km/h) exceeds safe foliar spray threshold ({FOLIAR_WIND_THRESHOLD} km/h) - high risk of spray drift.",
                next_window=next_window,
                forecast_summary=today,
                application_type=application_type,
                morning_window=morning_info,
                evening_window=evening_info,
                hourly_windows=hourly_windows,
            )
        if rain_prob >= FOLIAR_RAIN_PROB_THRESHOLD:
            next_window = _find_next_clear_day(forecast_days[1:], application_type="foliar")
            return ApplicationWindow(
                recommendation="YES",
                apply_today="WAIT",
                reason=f"Rain probability ({rain_prob}%) poses foliar spray wash-off risk.",
                next_window=next_window,
                forecast_summary=today,
                application_type=application_type,
                morning_window=morning_info,
                evening_window=evening_info,
                hourly_windows=hourly_windows,
            )

    # General soil application wind threshold (30 km/h)
    if wind >= WIND_KMH_THRESHOLD:
        next_window = _find_next_clear_day(forecast_days[1:], application_type=application_type)
        return ApplicationWindow(
            recommendation="YES",
            apply_today="WAIT",
            reason=f"High wind expected today ({wind} km/h) - unsuitable for spray/foliar application.",
            next_window=next_window,
            forecast_summary=today,
            application_type=application_type,
            morning_window=morning_info,
            evening_window=evening_info,
            hourly_windows=hourly_windows,
        )

    # If hourly window information exists, provide specific morning/evening guidance
    reason = "Forecast conditions today are within safe limits for application."
    if windows_hourly:
        m_stat = windows_hourly.get("morning", {}).get("status")
        e_stat = windows_hourly.get("evening", {}).get("status")
        if m_stat == "GO" and e_stat == "GO":
            reason += " Both morning (06:00-10:00) and evening (16:00-19:00) windows are favorable."
        elif e_stat == "GO":
            reason += " Evening window (16:00-19:00) is particularly favorable."
        elif m_stat == "GO":
            reason += " Morning window (06:00-10:00) is particularly favorable."

    return ApplicationWindow(
        recommendation="YES",
        apply_today="GO",
        reason=reason,
        forecast_summary=today,
        application_type=application_type,
        morning_window=morning_info,
        evening_window=evening_info,
        hourly_windows=hourly_windows,
    )


def _find_next_clear_day(remaining_days: list[dict], application_type: str = "general") -> str | None:
    wind_limit = FOLIAR_WIND_THRESHOLD if application_type == "foliar" else WIND_KMH_THRESHOLD
    rain_prob_limit = FOLIAR_RAIN_PROB_THRESHOLD if application_type == "foliar" else RAIN_PROB_THRESHOLD

    for day in remaining_days:
        rain = day.get("precipitation_mm") or 0
        rain_prob = day.get("precipitation_probability_pct") or 0
        wind = day.get("wind_max_kmh") or 0
        if rain < RAIN_MM_THRESHOLD and rain_prob < rain_prob_limit and wind < wind_limit:
            return day.get("date")
    return None
