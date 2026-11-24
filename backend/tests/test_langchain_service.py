"""Tests for LangChain Service Layer in AgriMind."""
import pytest
from app.models.soil import SoilReport, SoilValue
from app.models.crop import CropScore
from app.models.recommendation import Deficiency, FertilizerOption, ApplicationWindow, Evidence
from app.services.langchain_service import (
    build_structured_farm_context,
    get_session_history,
    clear_session_history,
    _build_deterministic_fallback,
    generate_langchain_explanation,
    generate_conversational_chat_response,
)


def test_build_structured_farm_context():
    soil = SoilReport(
        nitrogen=SoilValue(value=180, unit="kg/ha"),
        phosphorus=SoilValue(value=15, unit="kg/ha"),
        potassium=SoilValue(value=260, unit="kg/ha"),
        ph=SoilValue(value=6.4),
        organic_carbon=SoilValue(value=0.45, unit="%"),
        electrical_conductivity=SoilValue(value=0.32, unit="dS/m"),
        zinc=SoilValue(value=0.42, unit="ppm"),
    )
    deficiencies = [
        Deficiency(nutrient="nitrogen", status="LOW", detail="Nitrogen is LOW (180 kg/ha)."),
        Deficiency(nutrient="zinc", status="LOW", detail="Zinc is DEFICIENT (0.42 ppm)."),
    ]
    crop_scores = [
        CropScore(
            name="Tomato",
            score=82.0,
            ph_fit=True,
            n_fit=True,
            p_fit=True,
            k_fit=True,
            season_fit=True,
            reasons=["pH fits", "Available N meets requirement"],
        )
    ]
    fertilizer_options = [
        FertilizerOption(
            name="Urea (46% N)",
            type="chemical",
            nutrient="nitrogen",
            application_notes="Apply in 2 split doses.",
        )
    ]
    window = ApplicationWindow(
        recommendation="YES",
        apply_today="GO",
        reason="Conditions safe for application.",
        forecast_summary={"temp_min_c": 20, "temp_max_c": 30, "precipitation_mm": 0, "wind_max_kmh": 8, "humidity_max_pct": 55, "precipitation_probability_pct": 5},
    )
    evidence = [
        Evidence(text="Soil health card guidelines on nitrogen management.", source="soil/soil_health_card_guide.md", score=0.88)
    ]

    context = build_structured_farm_context(
        soil=soil,
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=window,
        evidence=evidence,
        location_name="Nagpur, Maharashtra",
        latitude=21.14,
        longitude=79.08,
    )

    assert "FARM LOCATION: Nagpur, Maharashtra" in context
    assert "Nitrogen: 180.0 kg/ha" in context
    assert "Zinc: 0.42 ppm" in context
    assert "Tomato: Score 82.0/100" in context
    assert "Urea (46% N)" in context
    assert "LIVE WEATHER & APPLICATION WINDOW" in context
    assert "soil/soil_health_card_guide.md" in context


def test_session_history_isolation():
    s1 = "farmer_alice_session"
    s2 = "farmer_bob_session"

    clear_session_history(s1)
    clear_session_history(s2)

    h1 = get_session_history(s1)
    h2 = get_session_history(s2)

    h1.add_user_message("What crop should I grow?")
    h1.add_ai_message("Tomato is suitable.")

    h2.add_user_message("Can I spray fertilizer today?")
    h2.add_ai_message("Yes, weather is clear.")

    assert len(h1.messages) == 2
    assert len(h2.messages) == 2
    assert "Tomato" in h1.messages[1].content
    assert "clear" in h2.messages[1].content


def test_deterministic_fallback_multilingual():
    deficiencies = [
        Deficiency(nutrient="nitrogen", status="LOW", detail="Nitrogen is low"),
    ]
    crop_scores = [
        CropScore(name="Tomato", score=85, ph_fit=True, n_fit=True, p_fit=True, k_fit=True, season_fit=True, reasons=[])
    ]
    fertilizer_options = [
        FertilizerOption(name="Urea", type="chemical", nutrient="nitrogen", application_notes="Apply split doses")
    ]

    en = _build_deterministic_fallback(deficiencies, crop_scores, fertilizer_options, None, [], "en")
    hi = _build_deterministic_fallback(deficiencies, crop_scores, fertilizer_options, None, [], "hi")
    mr = _build_deterministic_fallback(deficiencies, crop_scores, fertilizer_options, None, [], "mr")

    assert "low in" in en.lower()
    # Check Devanagari presence in Hindi and Marathi
    assert any("\u0900" <= ch <= "\u097f" for ch in hi)
    assert any("\u0900" <= ch <= "\u097f" for ch in mr)
