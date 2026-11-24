"""Agent 1 - Soil & Crop Recommendation Agent.

Combines soil data + (optional) selected crop + season with the
deterministic engine and RAG evidence. Does NOT call an LLM directly -
it produces structured facts that the LLM layer later explains.
"""
from __future__ import annotations

from app.models.soil import SoilReport
from app.models.recommendation import Deficiency, FertilizerOption
from app.models.crop import CropScore
from app.engine import crop_scorer, fertilizer_optimizer
from app.services.crop_service import get_crop
from app.rag.retriever import retrieve


class SoilAgentResult:
    def __init__(
        self,
        deficiencies: list[Deficiency],
        crop_scores: list[CropScore],
        fertilizer_options: list[FertilizerOption],
        evidence,
        contradiction: str | None,
    ):
        self.deficiencies = deficiencies
        self.crop_scores = crop_scores
        self.fertilizer_options = fertilizer_options
        self.evidence = evidence
        self.contradiction = contradiction


def run_soil_agent(
    soil: SoilReport,
    selected_crop: str | None,
    season: str | None,
    user_question: str | None,
    prefer_organic: bool = False,
) -> SoilAgentResult:
    deficiencies = fertilizer_optimizer.detect_deficiencies(soil)

    if selected_crop:
        crop = get_crop(selected_crop)
        crop_scores = [crop_scorer.score_crop(soil, crop, season)] if crop else []
    else:
        crop_scores = crop_scorer.rank_crops(soil, season)

    fertilizer_options = fertilizer_optimizer.recommend_fertilizers(deficiencies, prefer_organic=prefer_organic)

    contradiction = None
    if user_question:
        contradiction = fertilizer_optimizer.check_contradiction(user_question, deficiencies)

    # Build a retrieval query from the strongest signal we have.
    low_nutrients = [d.nutrient for d in deficiencies if d.status == "LOW"]
    query_parts = []
    if low_nutrients:
        query_parts.append(f"soil deficiency {' '.join(low_nutrients)}")
    if selected_crop:
        query_parts.append(f"{selected_crop} soil requirements")
    if user_question:
        query_parts.append(user_question)
    query_text = " ".join(query_parts) or "soil health general guidance"

    evidence = retrieve(query_text, top_k=4)

    return SoilAgentResult(
        deficiencies=deficiencies,
        crop_scores=crop_scores,
        fertilizer_options=fertilizer_options,
        evidence=evidence,
        contradiction=contradiction,
    )
