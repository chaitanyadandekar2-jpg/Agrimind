"""Agent - Weather & Application Timing Agent.

Fetches live forecast data (daily + hourly) and evaluates optimal application windows
for both soil incorporation and foliar spraying.
"""
from __future__ import annotations

from typing import Optional
from app.models.recommendation import ApplicationWindow
from app.services import weather_service
from app.engine.application_window import assess_application_window


async def run_weather_agent(
    latitude: float | None,
    longitude: float | None,
    needs_application: bool,
    application_type: str = "general",
) -> ApplicationWindow | None:
    if latitude is None or longitude is None:
        if not needs_application:
            return None
        return ApplicationWindow(
            recommendation="YES",
            apply_today="WAIT",
            reason="No farm location provided, so live weather forecast could not be checked.",
            application_type=application_type,
        )

    try:
        forecast = await weather_service.get_forecast(latitude, longitude)
    except weather_service.WeatherServiceError as exc:
        return ApplicationWindow(
            recommendation="YES" if needs_application else "NO",
            apply_today="WAIT",
            reason=f"Weather service error: {exc}",
            application_type=application_type,
        )

    days = forecast.get("days", [])
    windows_hourly = forecast.get("windows")
    spray_timeline = forecast.get("spray_timeline", [])

    return assess_application_window(
        forecast_days=days,
        needs_application=needs_application,
        application_type=application_type,
        windows_hourly=windows_hourly,
        hourly_windows=spray_timeline,
    )
