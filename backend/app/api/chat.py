from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.soil import SoilReport
from app.models.crop import CropScore
from app.models.recommendation import Deficiency, FertilizerOption, ApplicationWindow
from app.agents.crew_orchestrator import classify_query_intent
from app.agents.crew_agents import (
    execute_soil_analysis,
    execute_crop_recommendation,
    execute_fertilizer_optimization,
    execute_weather_intelligence,
    execute_knowledge_retrieval,
)
from app.services.weather_service import geocode_location
from app.services.langchain_service import (
    build_structured_farm_context,
    generate_conversational_chat_response,
)
from app.services.i18n import normalize_language

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "farmer_session_default"
    soil: Optional[SoilReport] = None
    selected_crop: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    season: Optional[str] = None
    prefer_organic: bool = False
    language: str = "en"  # "en" | "hi" | "mr"
    previous_crop_scores: Optional[List[CropScore]] = None
    previous_fertilizer_options: Optional[List[FertilizerOption]] = None
    previous_application_window: Optional[ApplicationWindow] = None


class ChatResponse(BaseModel):
    answer: str
    evidence: List[dict] = Field(default_factory=list)
    contradiction_flag: Optional[str] = None
    intent: Optional[str] = None
    clarification_needed: Optional[str] = None
    crop_scores: Optional[List[CropScore]] = None
    fertilizer_options: Optional[List[FertilizerOption]] = None
    application_window: Optional[ApplicationWindow] = None


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    lang = normalize_language(req.language)
    session_id = req.session_id or "farmer_session_default"

    # 1. Resolve Location Coordinates if needed
    lat = req.latitude
    lon = req.longitude
    if (lat is None or lon is None) and req.location_name:
        try:
            coords = await geocode_location(req.location_name)
            if coords:
                lat, lon = coords
        except Exception as exc:
            logger.warning(f"Geocoding failed for {req.location_name}: {exc}")

    # 2. Intent Classification
    intent_result = classify_query_intent(
        query=req.message,
        has_soil=bool(req.soil),
        has_location=bool(lat is not None and lon is not None),
    )

    # 3. Dynamic Context Generation & Agent Execution
    soil = req.soil or SoilReport()
    soil_analysis = execute_soil_analysis(soil)
    deficiencies = soil_analysis.deficiencies

    # Handle Crop Scoring
    crop_scores: List[CropScore] = req.previous_crop_scores or []
    if (not crop_scores or intent_result.needs_crop_scoring) and req.soil:
        crop_out = execute_crop_recommendation(
            soil=soil,
            selected_crop=req.selected_crop,
            season=req.season,
            top_n=5,
        )
        crop_scores = crop_out.crop_scores

    # Handle Fertilizer Optimization
    fertilizer_options: List[FertilizerOption] = req.previous_fertilizer_options or []
    contradiction = None
    if (not fertilizer_options or intent_result.needs_fertilizer_rec) and req.soil:
        fert_out = execute_fertilizer_optimization(
            deficiencies=deficiencies,
            prefer_organic=req.prefer_organic,
            user_question=req.message,
            crop_name=req.selected_crop,
        )
        fertilizer_options = fert_out.fertilizer_options
        contradiction = fert_out.contradiction_warning
    elif req.soil:
        fert_out = execute_fertilizer_optimization(
            deficiencies=deficiencies,
            prefer_organic=req.prefer_organic,
            user_question=req.message,
            crop_name=req.selected_crop,
        )
        contradiction = fert_out.contradiction_warning

    # Handle Weather & Spraying Windows
    application_window: Optional[ApplicationWindow] = req.previous_application_window
    if intent_result.needs_weather or not application_window:
        if lat is not None and lon is not None:
            # Check if spray window requested
            is_foliar = any(k in req.message.lower() for k in ["spray", "foliar", "spraying"])
            weather_out = await execute_weather_intelligence(
                latitude=lat,
                longitude=lon,
                needs_application=True,
                application_type="foliar" if is_foliar else "general",
            )
            application_window = weather_out.application_window

    # Handle RAG Knowledge Retrieval
    knowledge_out = execute_knowledge_retrieval(
        query_text=req.message,
        deficiencies=deficiencies,
        selected_crop=req.selected_crop,
        top_k=4,
    )
    evidence = knowledge_out.evidence

    # 4. Build Complete Grounded Farm Context
    contradictions_list = [contradiction] if contradiction else []
    farm_context = build_structured_farm_context(
        soil=soil if req.soil else None,
        deficiencies=deficiencies if req.soil else None,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=application_window,
        evidence=evidence,
        location_name=req.location_name,
        latitude=lat,
        longitude=lon,
        contradictions=contradictions_list,
    )

    # 5. Generate Conversational Chat Response via LangChain with Session Memory
    chat_result = await generate_conversational_chat_response(
        session_id=session_id,
        message=req.message,
        farm_context=farm_context,
        language=lang,
        contradiction_flag=contradiction,
        evidence=evidence,
    )

    return ChatResponse(
        answer=chat_result["answer"],
        evidence=chat_result["evidence"],
        contradiction_flag=contradiction,
        intent=intent_result.intent,
        clarification_needed=intent_result.clarification_question,
        crop_scores=crop_scores if crop_scores else None,
        fertilizer_options=fertilizer_options if fertilizer_options else None,
        application_window=application_window,
    )
