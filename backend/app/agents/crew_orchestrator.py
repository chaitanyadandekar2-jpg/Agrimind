"""CrewAI Central Orchestrator for AgriMind.

Coordinates specialized agricultural agents using conditional routing,
deterministic calculations, vector knowledge retrieval, and LangChain explanations.
"""
from __future__ import annotations

import re
import logging
from typing import Optional, Dict, Any, List

from app.models.soil import SoilReport
from app.models.recommendation import (
    RecommendationResponse,
    WhyThisRecommendation,
    Deficiency,
    FertilizerOption,
    ApplicationWindow,
    Evidence,
)
from app.models.crop import CropScore
from app.agents.crew_agents import (
    create_soil_analysis_agent,
    create_crop_recommendation_agent,
    create_fertilizer_optimization_agent,
    create_weather_intelligence_agent,
    create_agricultural_knowledge_agent,
    execute_soil_analysis,
    execute_crop_recommendation,
    execute_fertilizer_optimization,
    execute_weather_intelligence,
    execute_knowledge_retrieval,
    SoilAnalysisOutput,
    CropRecommendationOutput,
    FertilizerOptimizationOutput,
    WeatherIntelligenceOutput,
    KnowledgeRetrievalOutput,
)
from app.services.langchain_service import (
    build_structured_farm_context,
    generate_langchain_explanation,
    ChatIntentResult,
)
from app.services.i18n import normalize_language

logger = logging.getLogger(__name__)


def classify_query_intent(query: str, has_soil: bool, has_location: bool) -> ChatIntentResult:
    """Classifies user query intent to conditionally invoke only required agents."""
    q = query.lower()

    # Weather / spraying intent
    weather_keywords = ["spray", "rain", "wind", "weather", "temperature", "evening", "morning", "forecast", "tomorrow", "today", "window"]
    is_weather = any(k in q for k in weather_keywords)

    # Crop suitability intent
    crop_keywords = ["crop", "grow", "suitable", "suitability", "yield", "variety", "plant", "sow", "season", "wheat", "rice", "tomato", "cotton", "soybean", "onion", "sugarcane", "chickpea"]
    is_crop = any(k in q for k in crop_keywords)

    # Fertilizer & organic intent
    fertilizer_keywords = ["fertilizer", "urea", "dap", "ssp", "potash", "mop", "sop", "organic", "fym", "manure", "compost", "zinc", "iron", "sulphur", "deficiency", "npk", "dose", "dosage"]
    is_fertilizer = any(k in q for k in fertilizer_keywords)

    # Soil health intent
    soil_keywords = ["soil", "ph", "carbon", "oc", "saline", "ec", "salinity", "nitrogen", "phosphorus", "potassium", "acidic", "alkaline"]
    is_soil = any(k in q for k in soil_keywords)

    clarification = None
    if is_weather and not has_location:
        clarification = "To evaluate live weather or spray timing windows, please provide your farm location or city name."
    elif (is_soil or is_crop or is_fertilizer) and not has_soil:
        clarification = "To give personalized recommendations, please upload your soil test report PDF."

    if is_weather and not is_crop and not is_fertilizer:
        intent = "weather_query"
    elif is_crop and not is_fertilizer:
        intent = "crop_query"
    elif is_fertilizer and not is_crop:
        intent = "fertilizer_query"
    elif is_soil:
        intent = "soil_query"
    else:
        intent = "general_qna"

    return ChatIntentResult(
        intent=intent,
        needs_weather=is_weather or is_fertilizer,
        needs_crop_scoring=is_crop,
        needs_fertilizer_rec=is_fertilizer or is_soil,
        needs_rag=True,
        clarification_question=clarification,
    )


async def orchestrate_crew(
    soil: SoilReport,
    selected_crop: Optional[str] = None,
    season: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: Optional[str] = None,
    user_question: Optional[str] = None,
    prefer_organic: bool = False,
    language: str = "en",
) -> RecommendationResponse:
    """Full coordinated multi-agent workflow for AgriMind recommendations."""
    lang = normalize_language(language)

    # 1. Agent 1: Soil Analysis
    soil_out: SoilAnalysisOutput = execute_soil_analysis(soil)

    # 2. Agent 2: Crop Recommendation
    crop_out: CropRecommendationOutput = execute_crop_recommendation(
        soil=soil,
        selected_crop=selected_crop,
        season=season,
        top_n=6,
    )

    # 3. Agent 3: Fertilizer Optimization
    fertilizer_out: FertilizerOptimizationOutput = execute_fertilizer_optimization(
        deficiencies=soil_out.deficiencies,
        prefer_organic=prefer_organic,
        user_question=user_question,
        crop_name=selected_crop,
    )

    # 4. Agent 4: Weather Intelligence
    needs_application = len(fertilizer_out.fertilizer_options) > 0
    # Check if any foliar spray option was recommended
    has_foliar = any(f.application_method == "foliar" for f in fertilizer_out.fertilizer_options)
    app_type = "foliar" if has_foliar else "general"

    weather_out: WeatherIntelligenceOutput = await execute_weather_intelligence(
        latitude=latitude,
        longitude=longitude,
        needs_application=needs_application,
        application_type=app_type,
    )

    # 5. Agent 5: Agricultural Knowledge & RAG
    query_text = user_question or (f"{selected_crop or 'crop'} soil fertility management")
    knowledge_out: KnowledgeRetrievalOutput = execute_knowledge_retrieval(
        query_text=query_text,
        deficiencies=soil_out.deficiencies,
        selected_crop=selected_crop,
        top_k=4,
    )

    # 6. Consolidated Validation & Contradiction Resolution
    contradictions: List[str] = []
    if fertilizer_out.contradiction_warning:
        contradictions.append(fertilizer_out.contradiction_warning)

    # Build confidence metric
    confidence = soil.completeness()
    if contradictions:
        confidence = min(confidence, 0.5)

    weather_factor = None
    if weather_out.application_window:
        weather_factor = f"{weather_out.application_window.apply_today}: {weather_out.application_window.reason}"

    # Build structured evidence panel
    soil_reasons = []
    low_nutrients = [d.detail for d in soil_out.deficiencies if d.status == "LOW"]
    if low_nutrients:
        soil_reasons.extend(low_nutrients)
    else:
        soil_reasons.append("No critical nutrient deficiencies detected from available soil parameters.")

    why = WhyThisRecommendation(
        reason_soil=" ".join(soil_reasons),
        evidence=knowledge_out.evidence,
        weather_factor=weather_factor,
        confidence=confidence,
        contradictions=contradictions,
    )

    # 7. LangChain Explanation Layer
    farm_context = build_structured_farm_context(
        soil=soil,
        deficiencies=soil_out.deficiencies,
        crop_scores=crop_out.crop_scores,
        fertilizer_options=fertilizer_out.fertilizer_options,
        application_window=weather_out.application_window,
        evidence=knowledge_out.evidence,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        contradictions=contradictions,
    )

    llm_explanation = await generate_langchain_explanation(
        farm_context=farm_context,
        user_question=user_question,
        language=lang,
        deficiencies=soil_out.deficiencies,
        crop_scores=crop_out.crop_scores,
        fertilizer_options=fertilizer_out.fertilizer_options,
        application_window=weather_out.application_window,
        contradictions=contradictions,
    )

    return RecommendationResponse(
        soil=soil,
        deficiencies=soil_out.deficiencies,
        crop_scores=crop_out.crop_scores,
        fertilizer_options=fertilizer_out.fertilizer_options,
        application_window=weather_out.application_window,
        why=why,
        llm_explanation=llm_explanation,
        language=lang,
    )
