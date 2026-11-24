"""The LLM explanation layer, powered by LangChain.

Preserves backward compatibility while leveraging LangChain ChatOpenAI,
centralized prompts, and graceful deterministic fallbacks.
"""
from __future__ import annotations

from typing import Optional, List
from app.models.soil import SoilReport
from app.models.recommendation import Deficiency, FertilizerOption, ApplicationWindow, Evidence
from app.models.crop import CropScore
from app.services import i18n
from app.services.langchain_service import (
    build_structured_farm_context,
    generate_langchain_explanation,
    _build_deterministic_fallback,
)


def _build_context(
    soil: SoilReport,
    deficiencies: list[Deficiency],
    crop_scores: list[CropScore],
    fertilizer_options: list[FertilizerOption],
    application_window: ApplicationWindow | None,
    evidence: list[Evidence],
    user_question: str | None,
    contradictions: list[str],
) -> str:
    return build_structured_farm_context(
        soil=soil,
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=application_window,
        evidence=evidence,
        contradictions=contradictions,
    )


def _template_fallback(
    deficiencies: list[Deficiency],
    crop_scores: list[CropScore],
    fertilizer_options: list[FertilizerOption],
    application_window: ApplicationWindow | None,
    contradictions: list[str],
    language: str = "en",
) -> str:
    return _build_deterministic_fallback(
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=application_window,
        contradictions=contradictions,
        language=language,
    )


async def generate_explanation(
    soil: SoilReport,
    deficiencies: list[Deficiency],
    crop_scores: list[CropScore],
    fertilizer_options: list[FertilizerOption],
    application_window: ApplicationWindow | None,
    evidence: list[Evidence],
    user_question: str | None = None,
    contradictions: list[str] | None = None,
    language: str = "en",
) -> str:
    contradictions = contradictions or []
    lang = i18n.normalize_language(language)

    farm_context = build_structured_farm_context(
        soil=soil,
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=application_window,
        evidence=evidence,
        contradictions=contradictions,
    )

    return await generate_langchain_explanation(
        farm_context=farm_context,
        user_question=user_question,
        language=lang,
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        application_window=application_window,
        contradictions=contradictions,
    )
