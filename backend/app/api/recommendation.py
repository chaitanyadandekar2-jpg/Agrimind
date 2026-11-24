from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.soil import SoilReport
from app.models.recommendation import RecommendationResponse
from app.agents.crew_orchestrator import orchestrate_crew
from app.services.weather_service import geocode_location, WeatherServiceError
from app.services.i18n import normalize_language

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


class RecommendationRequest(BaseModel):
    soil: SoilReport
    selected_crop: str | None = None
    season: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    user_question: str | None = None
    prefer_organic: bool = False
    language: str = "en"  # "en" | "hi" | "mr"


@router.post("", response_model=RecommendationResponse)
async def get_recommendation(req: RecommendationRequest) -> RecommendationResponse:
    latitude, longitude = req.latitude, req.longitude

    if latitude is None and longitude is None and req.location_name:
        try:
            coords = await geocode_location(req.location_name)
            if coords:
                latitude, longitude = coords
        except Exception:
            # Continue without crashing if geocoding provider has rate limits or network issues
            pass

    return await orchestrate_crew(
        soil=req.soil,
        selected_crop=req.selected_crop,
        season=req.season,
        latitude=latitude,
        longitude=longitude,
        location_name=req.location_name,
        user_question=req.user_question,
        prefer_organic=req.prefer_organic,
        language=normalize_language(req.language),
    )
