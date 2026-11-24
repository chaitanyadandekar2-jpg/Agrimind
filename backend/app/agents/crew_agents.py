"""CrewAI Specialized Multi-Agent System for AgriMind.

Defines 5 specialized agricultural agents:
1. Soil Analysis Agent
2. Crop Recommendation Agent
3. Fertilizer Optimization Agent
4. Weather Intelligence Agent
5. Agricultural Knowledge & RAG Agent
"""
from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from crewai import Agent, LLM

from app.models.soil import SoilReport
from app.models.recommendation import Deficiency, FertilizerOption, ApplicationWindow, Evidence
from app.models.crop import CropScore
from app.engine import crop_scorer, fertilizer_optimizer, application_window
from app.services.crop_service import get_crop
from app.services import weather_service
from app.rag.langchain_retriever import retrieve_evidence


def get_crew_llm() -> LLM:
    """Configures LLM for CrewAI agents with fallback key to avoid crash when offline."""
    key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key_to_use = key if (key and not key.startswith("sk-your-key")) else "dummy-api-key"

    if "gemini" in model.lower():
        try:
            import google.genai  # noqa: F401
        except ImportError:
            model = "gpt-4o-mini"

    if base_url:
        return LLM(model=f"openai/{model}", api_key=api_key_to_use, base_url=base_url)
    return LLM(model=model, api_key=api_key_to_use)


# ---------------------------------------------------------------------------
# Structured Agent Outputs
# ---------------------------------------------------------------------------
class SoilAnalysisOutput(BaseModel):
    deficiencies: List[Deficiency] = Field(default_factory=list)
    ph_status: str = "NORMAL"
    oc_status: str = "NORMAL"
    ec_status: str = "NORMAL"
    missing_parameters: List[str] = Field(default_factory=list)
    completeness: float = 1.0


class CropRecommendationOutput(BaseModel):
    crop_scores: List[CropScore] = Field(default_factory=list)
    top_crop: Optional[str] = None
    season_evaluated: Optional[str] = None
    limiting_factors: List[str] = Field(default_factory=list)


class FertilizerOptimizationOutput(BaseModel):
    fertilizer_options: List[FertilizerOption] = Field(default_factory=list)
    contradiction_warning: Optional[str] = None
    active_deficiencies: List[str] = Field(default_factory=list)


class WeatherIntelligenceOutput(BaseModel):
    application_window: Optional[ApplicationWindow] = None
    location_label: Optional[str] = None
    is_spray_safe_today: bool = False
    morning_favorable: bool = False
    evening_favorable: bool = False


class KnowledgeRetrievalOutput(BaseModel):
    evidence: List[Evidence] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Specialized CrewAI Agent Factory Functions
# ---------------------------------------------------------------------------
def create_soil_analysis_agent() -> Agent:
    return Agent(
        role="Senior Agricultural Soil Chemist",
        goal="Analyze structured soil reports, determine accurate nutrient deficiency bands (LOW, MEDIUM, HIGH), evaluate pH, OC, and EC, detect missing parameters, and provide verified soil health assessments.",
        backstory=(
            "You are an expert soil agronomist with decades of experience interpreting Soil Health Cards and laboratory test reports. "
            "You strictly follow validated Soil Health Card rating scales (e.g. alkaline-permanganate N, Olsen P, NH4OAc K, DTPA micronutrients) "
            "and never fabricate or assume missing soil values."
        ),
        llm=get_crew_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_crop_recommendation_agent() -> Agent:
    return Agent(
        role="Crop Agronomy & Suitability Specialist",
        goal="Evaluate crop suitability based on soil chemistry, seasonal fit, salinity tolerance, and water requirements using the deterministic crop scoring engine, ranking top crops with transparent suitability reasons.",
        backstory=(
            "You are a crop scientist specializing in Indian cropping seasons (Kharif, Rabi, Zaid) and agro-climatic zones. "
            "You assess crop-soil compatibility transparently and detail the limiting factors for each crop."
        ),
        llm=get_crew_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_fertilizer_optimization_agent() -> Agent:
    return Agent(
        role="Plant Nutrition & Fertilizer Optimization Specialist",
        goal="Recommend targeted chemical fertilizers and organic soil amendments for identified nutrient deficiencies, distinguishing application methods (foliar vs soil) and growth-stage timing without inventing unvalidated dosages.",
        backstory=(
            "You are an expert in integrated plant nutrition management (IPNM). You balance rapid crop nutrition with long-term soil health. "
            "You strictly avoid recommending fertilizers for nutrients that are already HIGH in the soil."
        ),
        llm=get_crew_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_weather_intelligence_agent() -> Agent:
    return Agent(
        role="Agricultural Meteorologist & Application Timing Advisor",
        goal="Evaluate live meteorological conditions, hourly temperature, precipitation probability, wind speed, and humidity to determine safe and effective spray and soil fertilizer application windows.",
        backstory=(
            "You are a farm micrometeorologist specializing in spray drift management, volatilization reduction, and nutrient runoff prevention. "
            "You distinguish between foliar spraying conditions (requiring low wind and moderate temperature) and soil fertilizer incorporation."
        ),
        llm=get_crew_llm(),
        verbose=False,
        allow_delegation=False,
    )


def create_agricultural_knowledge_agent() -> Agent:
    return Agent(
        role="Agricultural Extension Knowledge Researcher",
        goal="Retrieve authoritative agricultural research documents, Soil Health Card guides, and organic farming practices from the vector database to ground all recommendations with verified source citations.",
        backstory=(
            "You are a dedicated agricultural researcher with access to the CGIAR Soil Health Framework, ICAR guidelines, and extension documentation. "
            "You cite exact sources and explicitly flag when evidence is insufficient."
        ),
        llm=get_crew_llm(),
        verbose=False,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Specialized Deterministic Agent Execution Logic
# ---------------------------------------------------------------------------
def execute_soil_analysis(soil: SoilReport) -> SoilAnalysisOutput:
    """Agent 1 Execution: Deterministic soil deficiency & parameter analysis."""
    deficiencies = fertilizer_optimizer.detect_deficiencies(soil)

    ph_status = "NORMAL"
    if soil.ph and soil.ph.value is not None:
        if soil.ph.value < 5.5:
            ph_status = "ACIDIC"
        elif soil.ph.value > 8.0:
            ph_status = "ALKALINE"

    oc_status = "NORMAL"
    if soil.organic_carbon and soil.organic_carbon.value is not None:
        if soil.organic_carbon.value < 0.5:
            oc_status = "LOW"

    ec_status = "NORMAL"
    if soil.electrical_conductivity and soil.electrical_conductivity.value is not None:
        if soil.electrical_conductivity.value > 2.0:
            ec_status = "SALINE"

    missing = [w for w in soil.extraction_warnings]
    return SoilAnalysisOutput(
        deficiencies=deficiencies,
        ph_status=ph_status,
        oc_status=oc_status,
        ec_status=ec_status,
        missing_parameters=missing,
        completeness=soil.completeness(),
    )


def execute_crop_recommendation(
    soil: SoilReport,
    selected_crop: Optional[str] = None,
    season: Optional[str] = None,
    top_n: int = 5,
) -> CropRecommendationOutput:
    """Agent 2 Execution: Deterministic crop scoring & ranking."""
    if selected_crop:
        crop_req = get_crop(selected_crop)
        scores = [crop_scorer.score_crop(soil, crop_req, season)] if crop_req else []
    else:
        scores = crop_scorer.rank_crops(soil, season, top_n=top_n)

    top_crop_name = scores[0].name if scores else None
    limiting = []
    for s in scores:
        if s.limiting_factors:
            limiting.extend(s.limiting_factors)

    return CropRecommendationOutput(
        crop_scores=scores,
        top_crop=top_crop_name,
        season_evaluated=season,
        limiting_factors=limiting,
    )


def execute_fertilizer_optimization(
    deficiencies: List[Deficiency],
    prefer_organic: bool = False,
    user_question: Optional[str] = None,
    crop_name: Optional[str] = None,
    method_filter: Optional[str] = None,
) -> FertilizerOptimizationOutput:
    """Agent 3 Execution: Deterministic fertilizer selection and contradiction check."""
    options = fertilizer_optimizer.recommend_fertilizers(
        deficiencies=deficiencies,
        prefer_organic=prefer_organic,
        method_filter=method_filter,
        crop_name=crop_name,
    )

    contradiction = None
    if user_question:
        contradiction = fertilizer_optimizer.check_contradiction(user_question, deficiencies)

    low_nutrients = [d.nutrient for d in deficiencies if d.status == "LOW"]
    return FertilizerOptimizationOutput(
        fertilizer_options=options,
        contradiction_warning=contradiction,
        active_deficiencies=low_nutrients,
    )


async def execute_weather_intelligence(
    latitude: Optional[float],
    longitude: Optional[float],
    needs_application: bool,
    application_type: str = "general",
) -> WeatherIntelligenceOutput:
    """Agent 4 Execution: Live forecast retrieval and application window calculation."""
    if latitude is None or longitude is None:
        window = None
        if needs_application:
            window = ApplicationWindow(
                recommendation="YES",
                apply_today="WAIT",
                reason="No farm location coordinates provided, so live weather could not be evaluated.",
                application_type=application_type,
            )
        return WeatherIntelligenceOutput(application_window=window)

    try:
        forecast = await weather_service.get_forecast(latitude, longitude)
    except weather_service.WeatherServiceError as exc:
        window = ApplicationWindow(
            recommendation="YES" if needs_application else "NO",
            apply_today="WAIT",
            reason=f"Weather service error: {exc}",
            application_type=application_type,
        )
        return WeatherIntelligenceOutput(application_window=window)

    days = forecast.get("days", [])
    windows_hourly = forecast.get("windows", {})
    spray_timeline = forecast.get("spray_timeline", [])
    window = application_window.assess_application_window(
        forecast_days=days,
        needs_application=needs_application,
        application_type=application_type,
        windows_hourly=windows_hourly,
        hourly_windows=spray_timeline,
    )

    m_fav = windows_hourly.get("morning", {}).get("status") == "GO"
    e_fav = windows_hourly.get("evening", {}).get("status") == "GO"

    return WeatherIntelligenceOutput(
        application_window=window,
        location_label=f"Coordinates ({latitude:.2f}, {longitude:.2f})",
        is_spray_safe_today=(window.apply_today == "GO"),
        morning_favorable=m_fav,
        evening_favorable=e_fav,
    )


def execute_knowledge_retrieval(
    query_text: str,
    deficiencies: Optional[List[Deficiency]] = None,
    selected_crop: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 4,
) -> KnowledgeRetrievalOutput:
    """Agent 5 Execution: ChromaDB RAG retrieval with query construction."""
    query_parts = [query_text]
    if selected_crop:
        query_parts.append(f"{selected_crop} soil requirements")
    if deficiencies:
        low_n = [d.nutrient for d in deficiencies if d.status == "LOW"]
        if low_n:
            query_parts.append(f"deficiency correction {' '.join(low_n)}")

    full_query = " ".join(query_parts).strip()
    evidence_items = retrieve_evidence(full_query, top_k=top_k, category=category)
    sources = list(set(e.source for e in evidence_items))

    return KnowledgeRetrievalOutput(
        evidence=evidence_items,
        sources=sources,
    )
