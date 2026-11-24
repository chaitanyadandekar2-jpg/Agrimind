"""Deterministic nutrient-status classification and fertilizer selection.

Thresholds follow the official Indian Soil Health Card fertility rating scale:
  - Nitrogen (alkaline permanganate): Low <280, Medium 280-560, High >560 kg/ha
  - Phosphorus (Olsen):               Low <10,  Medium 10-25,  High >25 kg/ha
  - Potassium (NH4OAc):               Low <108, Medium 108-280, High >280 kg/ha
  - Organic Carbon:                   Low <0.5, Medium 0.5-0.75, High >0.75 %
  - Zinc (DTPA):                      Deficient <0.6 ppm
  - Iron (DTPA):                      Deficient <4.5 ppm
  - Sulphur (0.15% CaCl2):            Deficient <10.0 ppm
"""
from __future__ import annotations

from typing import Optional, List
from app.models.soil import SoilReport
from app.models.recommendation import Deficiency, FertilizerOption
from app.services.fertilizer_service import get_options_for_nutrient

_THRESHOLDS = {
    "nitrogen": (280, 560),
    "phosphorus": (10, 25),
    "potassium": (108, 280),
    "organic_carbon": (0.5, 0.75),
}

_MICRONUTRIENT_CRITICAL = {
    "zinc": 0.6,
    "iron": 4.5,
    "sulphur": 10.0,
}


def _classify(value: float | None, thresholds: tuple[float, float]) -> str:
    if value is None:
        return "UNKNOWN"
    low, medium = thresholds
    if value < low:
        return "LOW"
    if value < medium:
        return "MEDIUM"
    return "HIGH"


def _classify_micronutrient(value: float | None, critical: float) -> str:
    if value is None:
        return "UNKNOWN"
    return "LOW" if value < critical else "HIGH"  # LOW=deficient, HIGH=sufficient


def detect_deficiencies(soil: SoilReport) -> list[Deficiency]:
    deficiencies: list[Deficiency] = []

    field_map = {
        "nitrogen": soil.nitrogen,
        "phosphorus": soil.phosphorus,
        "potassium": soil.potassium,
        "organic_carbon": soil.organic_carbon,
    }

    for nutrient, field in field_map.items():
        value = field.value if field else None
        status = _classify(value, _THRESHOLDS[nutrient])
        lo, hi = _THRESHOLDS[nutrient]
        unit = " %" if nutrient == "organic_carbon" else " kg/ha"
        threshold_desc = f"Low <{lo}, Medium {lo}-{hi}, High >{hi}{unit}"

        label = nutrient.replace("_", " ").title()
        if status == "UNKNOWN":
            detail = f"{label} value was not found in the uploaded report."
        elif status == "LOW":
            detail = f"{label} is LOW ({value}{unit}). Consider corrective fertilizer/amendment."
        elif status == "HIGH":
            detail = f"{label} is HIGH ({value}{unit}). Additional application is generally unnecessary."
        else:
            detail = f"{label} is at an adequate MEDIUM level ({value}{unit})."

        deficiencies.append(
            Deficiency(
                nutrient=nutrient,
                status=status,
                detail=detail,
                critical_threshold=threshold_desc,
            )
        )

    # Micronutrients: deficient / sufficient against single critical limit
    micronutrient_field_map = {
        "zinc": soil.zinc,
        "iron": soil.iron,
        "sulphur": soil.sulphur,
    }
    for nutrient, field in micronutrient_field_map.items():
        value = field.value if field else None
        critical = _MICRONUTRIENT_CRITICAL[nutrient]
        status = _classify_micronutrient(value, critical)
        label = nutrient.title()
        threshold_desc = f"Critical level: {critical} ppm"

        if status == "UNKNOWN":
            detail = f"{label} value was not found in the uploaded report."
        elif status == "LOW":
            detail = f"{label} is DEFICIENT ({value} ppm, critical level {critical} ppm). Correction recommended."
        else:
            detail = f"{label} is SUFFICIENT ({value} ppm, critical level {critical} ppm). No action needed."

        deficiencies.append(
            Deficiency(
                nutrient=nutrient,
                status=status,
                detail=detail,
                critical_threshold=threshold_desc,
            )
        )

    # pH and Electrical Conductivity
    if soil.ph and soil.ph.value is not None:
        ph_v = soil.ph.value
        if ph_v < 5.5:
            deficiencies.append(
                Deficiency(
                    nutrient="ph",
                    status="LOW",
                    detail=f"Soil is acidic (pH {ph_v}); liming may be needed.",
                    critical_threshold="Normal band: 6.0 - 7.5",
                )
            )
        elif ph_v > 8.0:
            deficiencies.append(
                Deficiency(
                    nutrient="ph",
                    status="HIGH",
                    detail=f"Soil is alkaline (pH {ph_v}); gypsum/organic matter may help.",
                    critical_threshold="Normal band: 6.0 - 7.5",
                )
            )

    if soil.electrical_conductivity and soil.electrical_conductivity.value is not None:
        ec_v = soil.electrical_conductivity.value
        if ec_v > 2.0:
            deficiencies.append(
                Deficiency(
                    nutrient="electrical_conductivity",
                    status="HIGH",
                    detail=f"EC is high ({ec_v} dS/m); only salt-tolerant crops advisable without remediation.",
                    critical_threshold="Safe non-saline limit < 1.0 - 2.0 dS/m",
                )
            )

    return deficiencies


def recommend_fertilizers(
    deficiencies: list[Deficiency],
    prefer_organic: bool = False,
    method_filter: Optional[str] = None,
    crop_name: Optional[str] = None,
) -> list[FertilizerOption]:
    """Recommend chemical and organic fertilizer options for LOW nutrients only.

    Features:
    - Never recommends nutrients that are MEDIUM or HIGH (prevents nutrient imbalance).
    - Distinguishes application methods (soil basal, foliar spray, organic incorporation).
    - Checks crop-specific considerations (e.g., chloride sensitivity, legume N-fixation).
    - Preserves agronomic validity without inventing ungrounded dosage numbers.
    """
    active_nutrients = ("nitrogen", "phosphorus", "potassium", "organic_carbon", "zinc", "iron", "sulphur")
    options: list[FertilizerOption] = []

    for d in deficiencies:
        if d.status != "LOW" or d.nutrient not in active_nutrients:
            continue

        data = get_options_for_nutrient(d.nutrient)
        chosen_types = ["organic", "chemical"] if prefer_organic else ["chemical", "organic"]

        for ftype in chosen_types:
            for item in data.get(ftype, []):
                method = item.get("application_method", "soil")
                if method_filter and method != method_filter:
                    continue

                compatibility = item.get("compatibility_notes")
                # Add crop-specific notes if relevant
                if crop_name:
                    c_low = crop_name.lower()
                    if "chickpea" in c_low or "soybean" in c_low:
                        if d.nutrient == "nitrogen" and ftype == "chemical":
                            compatibility = (compatibility or "") + " Note: Legumes fix atmospheric N; reduce chemical N to avoid vegetative lodging."
                    if "onion" in c_low or "tomato" in c_low:
                        if "mop" in item["name"].lower():
                            compatibility = (compatibility or "") + f" Caution: {crop_name} is chloride-sensitive; Sulphate of Potash (SOP) is preferred over MOP."

                options.append(
                    FertilizerOption(
                        name=item["name"],
                        type=ftype,
                        nutrient=d.nutrient,
                        application_method=method,
                        growth_stage=item.get("growth_stage"),
                        application_notes=item["application_notes"],
                        compatibility_notes=compatibility,
                        source=item.get("source"),
                    )
                )

    return options


def check_contradiction(user_question: str, deficiencies: list[Deficiency]) -> str | None:
    """Flags a contradiction when the user asks to add a nutrient that the
    soil report already shows as HIGH or ADEQUATE.
    """
    q = user_question.lower()
    nutrient_keywords = {
        "nitrogen": ["nitrogen", "urea"],
        "phosphorus": ["phosphorus", "phosphate", "dap", "ssp"],
        "potassium": ["potassium", "potash", "mop", "sop"],
        "zinc": ["zinc", "znso4", "zinc sulphate", "zinc sulfate"],
        "iron": ["iron", "feso4", "ferrous sulphate", "ferrous sulfate"],
        "sulphur": ["sulphur", "sulfur", "gypsum"],
    }
    for nutrient, keywords in nutrient_keywords.items():
        if any(k in q for k in keywords):
            match = next((d for d in deficiencies if d.nutrient == nutrient), None)
            if match and match.status == "HIGH":
                return (
                    f"Your soil report shows {nutrient.title()} is already HIGH. Adding more {nutrient} fertilizer "
                    f"is not recommended and could cause nutrient toxicity or ionic imbalance."
                )
    return None
