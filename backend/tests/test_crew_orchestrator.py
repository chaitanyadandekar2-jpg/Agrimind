"""Tests for Crew Orchestrator and Intent Classification."""
import pytest
from app.models.soil import SoilReport, SoilValue
from app.agents.crew_orchestrator import classify_query_intent, orchestrate_crew


def test_classify_query_intent_weather():
    res = classify_query_intent("Can I spray fertilizer this evening?", has_soil=True, has_location=True)
    assert res.needs_weather is True
    assert res.clarification_question is None

    # Missing location flags clarification
    res_no_loc = classify_query_intent("Can I spray fertilizer today?", has_soil=True, has_location=False)
    assert res_no_loc.needs_weather is True
    assert res_no_loc.clarification_question is not None
    assert "location" in res_no_loc.clarification_question.lower()


def test_classify_query_intent_crop():
    res = classify_query_intent("Which crop should I grow according to my soil?", has_soil=True, has_location=True)
    assert res.needs_crop_scoring is True
    assert res.intent == "crop_query"


def test_classify_query_intent_fertilizer():
    res = classify_query_intent("Which organic fertilizer can I use for nitrogen?", has_soil=True, has_location=True)
    assert res.needs_fertilizer_rec is True


@pytest.mark.asyncio
async def test_full_crew_orchestration():
    soil = SoilReport(
        nitrogen=SoilValue(value=180, unit="kg/ha"),
        phosphorus=SoilValue(value=15, unit="kg/ha"),
        potassium=SoilValue(value=260, unit="kg/ha"),
        ph=SoilValue(value=6.4),
        organic_carbon=SoilValue(value=0.45, unit="%"),
        electrical_conductivity=SoilValue(value=0.32, unit="dS/m"),
        zinc=SoilValue(value=0.42, unit="ppm"),
    )

    rec = await orchestrate_crew(
        soil=soil,
        selected_crop="Tomato",
        season="rabi",
        latitude=None,
        longitude=None,
        user_question="What should I do first?",
    )

    assert len(rec.deficiencies) > 0
    assert len(rec.crop_scores) > 0
    assert len(rec.fertilizer_options) > 0
    assert rec.why.confidence > 0
    assert rec.llm_explanation is not None
