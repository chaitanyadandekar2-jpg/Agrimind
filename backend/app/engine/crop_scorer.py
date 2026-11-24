"""Deterministic crop suitability scoring engine.

Calculates crop suitability without an LLM: compares soil test parameters
(pH, available N, P, K, Organic Carbon, Electrical Conductivity, and micronutrients)
along with seasonal fit against agronomic crop requirements.
"""
from __future__ import annotations

from typing import Optional, List
from app.models.soil import SoilReport
from app.models.crop import CropRequirement, CropScore
from app.services.crop_service import load_crop_requirements

# Base weights sum to 95; organic carbon contributes up to 5 points.
_WEIGHTS = {"ph": 25, "n": 20, "p": 15, "k": 15, "season": 20, "oc": 5}


def _in_range(value: float | None, lo: float, hi: float) -> bool:
    if value is None:
        return False
    return lo <= value <= hi


def score_crop(
    soil: SoilReport,
    crop: CropRequirement,
    current_season: str | None = None,
    water_availability: str | None = None,
) -> CropScore:
    reasons: list[str] = []
    limiting_factors: list[str] = []
    required_improvements: list[str] = []
    score = 0.0

    # 1. pH evaluation
    ph_val = soil.ph.value if soil.ph else None
    ph_fit = _in_range(ph_val, crop.ph_min, crop.ph_max)
    if ph_fit:
        score += _WEIGHTS["ph"]
        reasons.append(f"Soil pH {ph_val} is within {crop.name}'s preferred range ({crop.ph_min}-{crop.ph_max}).")
    elif ph_val is not None:
        gap = "acidic" if ph_val < crop.ph_min else "alkaline"
        reasons.append(f"Soil pH {ph_val} is {gap} for {crop.name} (ideal: {crop.ph_min}-{crop.ph_max}).")
        limiting_factors.append(f"Soil pH ({ph_val}) outside optimum range ({crop.ph_min}-{crop.ph_max}).")
        if ph_val < 5.5:
            required_improvements.append("Apply agricultural lime to raise soil pH before planting.")
        elif ph_val > 8.0:
            required_improvements.append("Incorporate gypsum and organic matter to lower soil alkalinity.")
    else:
        reasons.append("Soil pH was not available, so pH fit could not be scored.")

    # 2. Nitrogen evaluation
    n_val = soil.nitrogen.value if soil.nitrogen else None
    n_fit = _in_range(n_val, crop.n_min, crop.n_max)
    if n_fit:
        score += _WEIGHTS["n"]
        reasons.append(f"Available nitrogen ({n_val} kg/ha) meets {crop.name}'s requirement ({crop.n_min}-{crop.n_max} kg/ha).")
    elif n_val is not None:
        gap = "below" if n_val < crop.n_min else "above"
        reasons.append(f"Available nitrogen ({n_val} kg/ha) is {gap} {crop.name}'s ideal range ({crop.n_min}-{crop.n_max} kg/ha).")
        if n_val < crop.n_min:
            limiting_factors.append(f"Available nitrogen is low ({n_val} kg/ha).")
            required_improvements.append(f"Apply split nitrogen doses (e.g., Urea/Ammonium Sulphate) or enriched compost.")
        else:
            reasons.append(f"Elevated nitrogen present; adjust basal N to prevent lodging.")
    else:
        reasons.append("Available nitrogen was not reported.")

    # 3. Phosphorus evaluation
    p_val = soil.phosphorus.value if soil.phosphorus else None
    p_fit = _in_range(p_val, crop.p_min, crop.p_max)
    if p_fit:
        score += _WEIGHTS["p"]
        reasons.append(f"Available phosphorus ({p_val} kg/ha) meets {crop.name}'s requirement ({crop.p_min}-{crop.p_max} kg/ha).")
    elif p_val is not None:
        gap = "below" if p_val < crop.p_min else "above"
        reasons.append(f"Available phosphorus ({p_val} kg/ha) is {gap} {crop.name}'s ideal range.")
        if p_val < crop.p_min:
            limiting_factors.append(f"Phosphorus deficiency ({p_val} kg/ha vs required {crop.p_min}-{crop.p_max} kg/ha).")
            required_improvements.append("Apply basal phosphatic fertilizer (SSP/DAP or rock phosphate).")
    else:
        reasons.append("Available phosphorus was not reported.")

    # 4. Potassium evaluation
    k_val = soil.potassium.value if soil.potassium else None
    k_fit = _in_range(k_val, crop.k_min, crop.k_max)
    if k_fit:
        score += _WEIGHTS["k"]
        reasons.append(f"Available potassium ({k_val} kg/ha) meets {crop.name}'s requirement ({crop.k_min}-{crop.k_max} kg/ha).")
    elif k_val is not None:
        gap = "below" if k_val < crop.k_min else "above"
        reasons.append(f"Available potassium ({k_val} kg/ha) is {gap} {crop.name}'s ideal range.")
        if k_val < crop.k_min:
            limiting_factors.append(f"Potassium deficiency ({k_val} kg/ha vs required {crop.k_min}-{crop.k_max} kg/ha).")
            required_improvements.append("Apply potassium fertilizer (Muriate of Potash or Sulphate of Potash).")
    else:
        reasons.append("Available potassium was not reported.")

    # 5. Seasonal fit
    season_fit = current_season is None or current_season.lower() in [s.lower() for s in crop.season]
    if season_fit:
        score += _WEIGHTS["season"]
        if current_season:
            reasons.append(f"{crop.name} is suitable for the {current_season} season.")
    else:
        reasons.append(f"{crop.name} is typically grown in {', '.join(crop.season)}, not {current_season}.")
        limiting_factors.append(f"Off-season: {crop.name} is recommended for {', '.join(crop.season)}, not {current_season}.")

    # 6. Organic Carbon evaluation (0-5 points)
    oc_val = soil.organic_carbon.value if soil.organic_carbon else None
    oc_fit = None
    if oc_val is not None and crop.oc_min is not None:
        oc_fit = oc_val >= crop.oc_min
        if oc_fit:
            score += _WEIGHTS["oc"]
            reasons.append(f"Soil organic carbon ({oc_val}%) satisfies {crop.name}'s benchmark (min {crop.oc_min}%).")
        else:
            limiting_factors.append(f"Soil organic carbon ({oc_val}%) is below optimal benchmark ({crop.oc_min}%).")
            required_improvements.append("Apply 5-10 tonnes/ha well-decomposed FYM or vermicompost to build soil carbon.")
    elif oc_val is not None:
        # Default benchmark 0.5%
        oc_fit = oc_val >= 0.5
        if oc_fit:
            score += _WEIGHTS["oc"]

    # 7. Salinity (Electrical Conductivity) evaluation
    ec_val = soil.electrical_conductivity.value if soil.electrical_conductivity else None
    ec_fit = None
    if ec_val is not None and crop.ec_max is not None:
        ec_fit = ec_val <= crop.ec_max
        if not ec_fit:
            score = max(0.0, score - 15.0)  # Salinity penalty
            limiting_factors.append(f"Soil salinity EC ({ec_val} dS/m) exceeds {crop.name}'s salt tolerance ({crop.ec_max} dS/m).")
            required_improvements.append("Improve field drainage and apply organic amendments to mitigate salt stress.")
        else:
            reasons.append(f"Soil salinity ({ec_val} dS/m) is safely below {crop.name}'s tolerance limit ({crop.ec_max} dS/m).")

    # 8. Micronutrient impact on requirements
    if soil.zinc and soil.zinc.value is not None and soil.zinc.value < 0.6:
        required_improvements.append("Soil is deficient in Zinc (<0.6 ppm); apply 25 kg/ha ZnSO4 basal or 0.5% foliar spray.")
    if soil.iron and soil.iron.value is not None and soil.iron.value < 4.5:
        required_improvements.append("Soil is deficient in Iron (<4.5 ppm); apply ferrous sulphate foliar spray.")

    final_score = round(min(100.0, max(0.0, score)), 1)

    # Suitability Category
    if final_score >= 80.0:
        suitability_category = "Highly Suitable"
    elif final_score >= 60.0:
        suitability_category = "Suitable"
    elif final_score >= 40.0:
        suitability_category = "Marginally Suitable"
    else:
        suitability_category = "Unsuitable"

    return CropScore(
        name=crop.name,
        score=final_score,
        ph_fit=ph_fit,
        n_fit=n_fit,
        p_fit=p_fit,
        k_fit=k_fit,
        season_fit=season_fit,
        oc_fit=oc_fit,
        ec_fit=ec_fit,
        suitability_category=suitability_category,
        limiting_factors=limiting_factors,
        required_improvements=required_improvements,
        source=crop.source,
        reasons=reasons,
    )


def rank_crops(
    soil: SoilReport,
    current_season: str | None = None,
    water_availability: str | None = None,
    top_n: int = 5,
) -> list[CropScore]:
    """Score and rank all registered crops from data/knowledge/crops."""
    crops = load_crop_requirements()
    scores = [score_crop(soil, crop, current_season, water_availability) for crop in crops]
    scores.sort(key=lambda s: s.score, reverse=True)
    return scores[:top_n]
