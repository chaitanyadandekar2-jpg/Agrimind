from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


class CropRequirement(BaseModel):
    """Reference requirements for a crop, loaded from data/knowledge/crops."""

    name: str
    ph_min: float
    ph_max: float
    n_min: float           # kg/ha, minimum recommended available N
    n_max: float
    p_min: float
    p_max: float
    k_min: float
    k_max: float
    season: list[str]      # e.g. ["kharif", "rabi", "zaid"]
    water_need: str        # "low" | "medium" | "high"
    notes: Optional[str] = None
    oc_min: Optional[float] = None      # % organic carbon preferred
    ec_max: Optional[float] = None      # dS/m max threshold before yield penalty
    source: Optional[str] = None


class CropScore(BaseModel):
    name: str
    score: float            # 0-100
    ph_fit: bool
    n_fit: bool
    p_fit: bool
    k_fit: bool
    season_fit: bool
    reasons: list[str]
    oc_fit: Optional[bool] = None
    ec_fit: Optional[bool] = None
    suitability_category: Optional[str] = None  # "Highly Suitable" | "Suitable" | "Marginally Suitable" | "Unsuitable"
    limiting_factors: list[str] = Field(default_factory=list)
    required_improvements: list[str] = Field(default_factory=list)
    source: Optional[str] = None
