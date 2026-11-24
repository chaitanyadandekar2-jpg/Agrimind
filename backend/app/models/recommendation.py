from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.soil import SoilReport
from app.models.crop import CropScore


class Deficiency(BaseModel):
    nutrient: str
    status: str              # "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"
    detail: str
    critical_threshold: Optional[str] = None


class FertilizerOption(BaseModel):
    name: str
    type: str                 # "chemical" | "organic"
    nutrient: str
    application_notes: str
    application_method: str = "soil"  # "soil" | "foliar" | "fertigation" | "organic_incorporation"
    growth_stage: Optional[str] = None  # "Basal / At Sowing", "Vegetative Split", "Foliar Spray"
    source: Optional[str] = None
    compatibility_notes: Optional[str] = None


class Evidence(BaseModel):
    text: str
    source: str
    score: float


class ApplicationWindow(BaseModel):
    recommendation: str        # "YES" | "NO" | "CONDITIONAL"
    apply_today: str           # "GO" | "WAIT"
    reason: str
    next_window: Optional[str] = None
    forecast_summary: Optional[Dict[str, Any]] = None
    application_type: str = "general"  # "foliar" | "soil" | "general"
    morning_window: Optional[str] = None
    evening_window: Optional[str] = None
    hourly_windows: Optional[List[Dict[str, Any]]] = None


class WhyThisRecommendation(BaseModel):
    reason_soil: str
    evidence: List[Evidence]
    weather_factor: Optional[str] = None
    confidence: float          # 0-1
    contradictions: List[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    soil: SoilReport
    deficiencies: List[Deficiency]
    crop_scores: List[CropScore]
    fertilizer_options: List[FertilizerOption]
    application_window: Optional[ApplicationWindow] = None
    why: WhyThisRecommendation
    llm_explanation: Optional[str] = None
    language: str = "en"  # language the llm_explanation was generated in
