from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.weather_service import get_forecast, geocode_location, WeatherServiceError

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/forecast")
async def forecast(
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    location_name: str | None = Query(None),
):
    if (latitude is None or longitude is None) and location_name:
        try:
            coords = await geocode_location(location_name)
        except WeatherServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not coords:
            raise HTTPException(status_code=404, detail=f"Could not resolve location '{location_name}'.")
        latitude, longitude = coords

    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Provide either lat/lon or a location_name.")

    try:
        return await get_forecast(latitude, longitude)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
