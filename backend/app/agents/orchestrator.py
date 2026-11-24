"""Agent Orchestrator.

Routes calls to the CrewAI multi-agent orchestrator while preserving
full backwards compatibility for existing API endpoints.
"""
from __future__ import annotations

from typing import Optional
from app.models.soil import SoilReport
from app.models.recommendation import RecommendationResponse
from app.agents.crew_orchestrator import orchestrate_crew


async def orchestrate(
    soil: SoilReport,
    selected_crop: str | None,
    season: str | None,
    latitude: float | None,
    longitude: float | None,
    user_question: str | None,
    prefer_organic: bool = False,
    language: str = "en",
) -> RecommendationResponse:
    """Delegate to CrewAI multi-agent orchestrator."""
    return await orchestrate_crew(
        soil=soil,
        selected_crop=selected_crop,
        season=season,
        latitude=latitude,
        longitude=longitude,
        user_question=user_question,
        prefer_organic=prefer_organic,
        language=language,
    )
