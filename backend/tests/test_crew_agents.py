"""Tests for CrewAI Specialized Agricultural Agents."""
import pytest
from app.models.soil import SoilReport, SoilValue
from app.models.recommendation import Deficiency
from app.agents.crew_agents import (
    create_soil_analysis_agent,
    create_crop_recommendation_agent,
    create_fertilizer_optimization_agent,
    create_weather_intelligence_agent,
    create_agricultural_knowledge_agent,
    execute_soil_analysis,
    execute_crop_recommendation,
    execute_fertilizer_optimization,
    execute_knowledge_retrieval,
)


def test_agent_definitions_and_roles():
    a1 = create_soil_analysis_agent()
    assert "Soil" in a1.role
    assert a1.allow_delegation is False

    a2 = create_crop_recommendation_agent()
    assert "Crop" in a2.role

    a3 = create_fertilizer_optimization_agent()
    assert "Fertilizer" in a3.role

    a4 = create_weather_intelligence_agent()
    assert "Meteorologist" in a4.role or "Weather" in a4.role

    a5 = create_agricultural_knowledge_agent()
    assert "Knowledge" in a5.role or "Researcher" in a5.role


def test_execute_soil_analysis():
    soil = SoilReport(
        nitrogen=SoilValue(value=180, unit="kg/ha"),
        phosphorus=SoilValue(value=15, unit="kg/ha"),
        potassium=SoilValue(value=260, unit="kg/ha"),
        ph=SoilValue(value=6.4),
        organic_carbon=SoilValue(value=0.45, unit="%"),
        electrical_conductivity=SoilValue(value=0.32, unit="dS/m"),
        zinc=SoilValue(value=0.42, unit="ppm"),
    )
    result = execute_soil_analysis(soil)
    assert result.completeness == 1.0
    assert result.oc_status == "LOW"
    assert result.ph_status == "NORMAL"
    low_nutrients = [d.nutrient for d in result.deficiencies if d.status == "LOW"]
    assert "nitrogen" in low_nutrients
    assert "organic_carbon" in low_nutrients
    assert "zinc" in low_nutrients


def test_execute_crop_recommendation():
    soil = SoilReport(
        nitrogen=SoilValue(value=180, unit="kg/ha"),
        phosphorus=SoilValue(value=15, unit="kg/ha"),
        potassium=SoilValue(value=260, unit="kg/ha"),
        ph=SoilValue(value=6.4),
        organic_carbon=SoilValue(value=0.55, unit="%"),
        electrical_conductivity=SoilValue(value=0.32, unit="dS/m"),
    )
    result = execute_crop_recommendation(soil, season="rabi", top_n=5)
    assert len(result.crop_scores) > 0
    assert result.top_crop is not None
    # High scoring crop in rabi
    assert any(s.score >= 70 for s in result.crop_scores)


def test_execute_fertilizer_optimization():
    deficiencies = [
        Deficiency(nutrient="nitrogen", status="LOW", detail="Low nitrogen"),
        Deficiency(nutrient="potassium", status="HIGH", detail="High potassium"),
    ]
    result = execute_fertilizer_optimization(deficiencies, prefer_organic=False)
    assert len(result.fertilizer_options) > 0
    # Nitrogen options present, Potassium options NOT present (preventing excess)
    assert any(f.nutrient == "nitrogen" for f in result.fertilizer_options)
    assert not any(f.nutrient == "potassium" for f in result.fertilizer_options)


def test_execute_knowledge_retrieval():
    result = execute_knowledge_retrieval("soil nitrogen management", top_k=3)
    assert isinstance(result.evidence, list)
