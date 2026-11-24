"""LangChain Service Layer for AgriMind.

Provides:
- LLM configuration via ChatOpenAI (replaceable model, supports OpenAI & local/compatible endpoints).
- Centralized agricultural prompt templates.
- Pydantic structured output models.
- Conversational session memory (per-farmer session isolation).
- Agricultural RAG QA chain.
- Multilingual explanation support (English, Hindi, Marathi).
- Graceful deterministic fallback when no API key is provided or on network/API failure.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.services import i18n
from app.models.soil import SoilReport
from app.models.recommendation import Deficiency, FertilizerOption, ApplicationWindow, Evidence
from app.models.crop import CropScore

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None

# ---------------------------------------------------------------------------
# Structured Output Schemas
# ---------------------------------------------------------------------------
class StructuredAgriculturalExplanation(BaseModel):
    summary: str = Field(description="Short summary of farm status and key recommendations")
    soil_insights: List[str] = Field(default_factory=list, description="Specific insights on soil nutrients, pH, OC")
    crop_guidance: List[str] = Field(default_factory=list, description="Guidance on crop suitability and limits")
    fertilizer_actions: List[str] = Field(default_factory=list, description="Recommended fertilizers and amendments")
    weather_advisory: Optional[str] = Field(default=None, description="Spray/application timing advice based on weather")
    cautions: List[str] = Field(default_factory=list, description="Nutrient contradictions, runoff risks, or spray warnings")


class ChatIntentResult(BaseModel):
    intent: str = Field(description="One of: soil_query, crop_query, fertilizer_query, weather_query, general_qna")
    needs_weather: bool = Field(default=False)
    needs_crop_scoring: bool = Field(default=False)
    needs_fertilizer_rec: bool = Field(default=False)
    needs_rag: bool = Field(default=True)
    clarification_question: Optional[str] = Field(default=None, description="Ask farmer if crucial info is missing")


# ---------------------------------------------------------------------------
# Session Memory Management (Isolated per session)
# ---------------------------------------------------------------------------
_session_store: Dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Retrieve or create an in-memory chat message history for the given session."""
    if session_id not in _session_store:
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]


def clear_session_history(session_id: str) -> None:
    """Clear history for a specific session."""
    if session_id in _session_store:
        del _session_store[session_id]


# ---------------------------------------------------------------------------
# Chat Model Factory
# ---------------------------------------------------------------------------
def get_chat_model(temperature: float = 0.3) -> Optional[ChatOpenAI]:
    """Instantiate a ChatOpenAI model if an API key or base URL is present.
    Returns None if neither is available so deterministic fallback can be used.
    """
    key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model_name = os.getenv("OPENAI_MODEL", OPENAI_MODEL)

    # Treat empty or placeholder keys as unconfigured
    if not key or key.startswith("sk-your-key"):
        return None

    api_key_to_use = key or "dummy-key-for-local-llm"
    return ChatOpenAI(
        model=model_name,
        api_key=api_key_to_use,
        base_url=base_url or None,
        temperature=temperature,
        timeout=10.0,
        max_retries=1,
    )


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------
SYSTEM_EXPLANATION_PROMPT = """You are AgriMind's explainable agricultural decision-support assistant.
You provide farmers with clear, encouraging, practical, and evidence-grounded farming advice.

STRICT PRINCIPLES:
1. You are given ALREADY-COMPUTED deterministic facts: soil status, nutrient classifications, crop scores, fertilizer options, live weather, and retrieved evidence.
2. NEVER invent numbers, chemical dosages, or facts not present in the provided data.
3. If information is missing or uncertain, state so plainly and ask a constructive clarification question rather than guessing.
4. Keep the tone practical, respectful, and farmer-friendly.
5. Reference retrieved sources naturally (e.g., 'According to the Soil Health Card guidelines...', 'Per the CGIAR framework...') without inventing sources.
6. When discussing fertilizer application, distinguish between soil incorporation (basal) and foliar spraying.
7. Always observe contradictory flags (e.g., never recommend adding potassium if the report shows potassium is already HIGH).

{language_instruction}
"""

USER_EXPLANATION_TEMPLATE = """FARM AND RECOMMENDATION CONTEXT:
{farm_context}

FARMER'S QUESTION OR REQUEST:
{user_question}

Provide a clear, practical, and evidence-based explanation for the farmer.
"""

CHAT_SYSTEM_PROMPT = """You are AgriMind, an intelligent, multi-agent agricultural AI advisor.
You are interacting directly with a farmer.

STRICT PRINCIPLES:
1. Use the provided farm data (Soil report, Location, Crops, Fertilizer recommendations, Live weather) to answer accurately.
2. If the farmer asks a question requiring missing data (e.g. asking for spray advice with no location or weather), clearly explain what is missing and ask for it.
3. Never invent crop scores or unsupported chemical dosages.
4. If a contradiction is flagged (e.g. farmer wants to add a nutrient that is already HIGH in soil), warn them clearly.
5. If the farmer asks in Hindi or Marathi, respond in that language; otherwise respond in the requested language.

{language_instruction}
"""

# ---------------------------------------------------------------------------
# Context Builder
# ---------------------------------------------------------------------------
def build_structured_farm_context(
    soil: Optional[SoilReport] = None,
    deficiencies: Optional[List[Deficiency]] = None,
    crop_scores: Optional[List[CropScore]] = None,
    fertilizer_options: Optional[List[FertilizerOption]] = None,
    application_window: Optional[ApplicationWindow] = None,
    evidence: Optional[List[Evidence]] = None,
    location_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    contradictions: Optional[List[str]] = None,
) -> str:
    lines: List[str] = []

    if location_name or (latitude is not None and longitude is not None):
        loc_str = location_name or f"Coordinates ({latitude:.2f}, {longitude:.2f})"
        lines.append(f"FARM LOCATION: {loc_str}")

    if soil:
        completeness = soil.completeness() * 100
        lines.append(f"SOIL REPORT (Completeness: {completeness:.0f}%):")
        fields = [
            ("Nitrogen", soil.nitrogen),
            ("Phosphorus", soil.phosphorus),
            ("Potassium", soil.potassium),
            ("pH", soil.ph),
            ("Organic Carbon", soil.organic_carbon),
            ("Electrical Conductivity (EC)", soil.electrical_conductivity),
            ("Zinc", soil.zinc),
            ("Iron", soil.iron),
            ("Sulphur", soil.sulphur),
            ("Boron", soil.boron),
        ]
        for name, f in fields:
            if f and f.value is not None:
                unit = f" {f.unit}" if f.unit else ""
                lines.append(f"  - {name}: {f.value}{unit}")
            else:
                lines.append(f"  - {name}: Not measured / Missing")

    if deficiencies:
        lines.append("\nNUTRIENT STATUS CLASSIFICATION:")
        for d in deficiencies:
            lines.append(f"  - {d.nutrient.replace('_', ' ').title()}: {d.status} ({d.detail})")

    if crop_scores:
        lines.append("\nCROP SUITABILITY SCORES (Deterministic engine):")
        for c in crop_scores[:6]:
            reasons_str = "; ".join(c.reasons[:3]) if c.reasons else "Evaluated"
            lines.append(f"  - {c.name}: Score {c.score}/100 | {reasons_str}")

    if fertilizer_options:
        lines.append("\nRECOMMENDED FERTILIZERS & AMENDMENTS:")
        for f in fertilizer_options:
            src = f" (Source: {f.source})" if f.source else ""
            lines.append(f"  - [{f.type.upper()}] {f.name} for {f.nutrient}: {f.application_notes}{src}")
    else:
        lines.append("\nFERTILIZER OPTIONS: None recommended or nutrients already adequate.")

    if application_window:
        lines.append("\nLIVE WEATHER & APPLICATION WINDOW:")
        lines.append(f"  - Status: {application_window.apply_today} (Recommendation: {application_window.recommendation})")
        lines.append(f"  - Assessment: {application_window.reason}")
        if application_window.next_window:
            lines.append(f"  - Next clear window: {application_window.next_window}")
        if application_window.forecast_summary:
            f = application_window.forecast_summary
            lines.append(
                f"  - Forecast metrics: Temp {f.get('temp_min_c')}°C - {f.get('temp_max_c')}°C, "
                f"Rain {f.get('precipitation_mm')}mm ({f.get('precipitation_probability_pct')}%), "
                f"Wind {f.get('wind_max_kmh')} km/h, Humidity {f.get('humidity_max_pct')}%"
            )

    if contradictions:
        lines.append("\nCONTRADICTIONS / ALERTS:")
        for c in contradictions:
            lines.append(f"  - ⚠ {c}")

    if evidence:
        lines.append("\nRETRIEVED KNOWLEDGE BASE EVIDENCE:")
        for e in evidence:
            lines.append(f"  - [{e.source}] (Relevance {e.score}): {e.text[:250]}...")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core LangChain Generation Functions
# ---------------------------------------------------------------------------
async def generate_langchain_explanation(
    farm_context: str,
    user_question: Optional[str] = None,
    language: str = "en",
    deficiencies: Optional[List[Deficiency]] = None,
    crop_scores: Optional[List[CropScore]] = None,
    fertilizer_options: Optional[List[FertilizerOption]] = None,
    application_window: Optional[ApplicationWindow] = None,
    contradictions: Optional[List[str]] = None,
) -> str:
    """Generate an explanation using LangChain ChatOpenAI.
    Falls back gracefully to i18n template if LLM is unavailable.
    """
    lang = i18n.normalize_language(language)
    model = get_chat_model(temperature=0.3)

    if not model:
        # Graceful template fallback
        return _build_deterministic_fallback(
            deficiencies or [],
            crop_scores or [],
            fertilizer_options or [],
            application_window,
            contradictions or [],
            lang,
        )

    try:
        lang_instruction = i18n.llm_language_instruction(lang)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_EXPLANATION_PROMPT),
            ("user", USER_EXPLANATION_TEMPLATE),
        ])

        chain = prompt | model | StrOutputParser()
        response = await chain.ainvoke({
            "language_instruction": lang_instruction,
            "farm_context": farm_context,
            "user_question": user_question or "Please explain my farm soil status and recommendations.",
        })
        return response.strip()

    except Exception as exc:
        logger.warning(f"LangChain explanation generation failed: {exc}. Using deterministic fallback.")
        fallback = _build_deterministic_fallback(
            deficiencies or [],
            crop_scores or [],
            fertilizer_options or [],
            application_window,
            contradictions or [],
            lang,
        )
        return f"{fallback}\n\n[Note: Generated via deterministic fallback due to service note: {exc}]"


async def generate_conversational_chat_response(
    session_id: str,
    message: str,
    farm_context: str,
    language: str = "en",
    contradiction_flag: Optional[str] = None,
    evidence: Optional[List[Evidence]] = None,
) -> Dict[str, Any]:
    """Execute conversational chat with session memory and context grounding."""
    lang = i18n.normalize_language(language)
    history = get_session_history(session_id)
    model = get_chat_model(temperature=0.3)

    # Format recent history (keep last 6 messages to stay concise)
    recent_messages = history.messages[-6:] if history.messages else []

    if not model:
        # Deterministic context-aware response when no LLM key
        ans = _generate_fallback_chat_answer(message, farm_context, contradiction_flag, lang, evidence)
        history.add_user_message(message)
        history.add_ai_message(ans)
        return {
            "answer": ans,
            "contradiction_flag": contradiction_flag,
            "evidence": [e.model_dump() for e in (evidence or [])],
        }

    try:
        lang_instruction = i18n.llm_language_instruction(lang)
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "FARM DATA AND CURRENT RECOMMENDATIONS:\n{farm_context}\n\nFARMER QUESTION: {message}"),
        ])

        chain = prompt | model | StrOutputParser()
        response = await chain.ainvoke({
            "language_instruction": lang_instruction,
            "chat_history": recent_messages,
            "farm_context": farm_context,
            "message": message,
        })

        answer = response.strip()
        history.add_user_message(message)
        history.add_ai_message(answer)

        return {
            "answer": answer,
            "contradiction_flag": contradiction_flag,
            "evidence": [e.model_dump() for e in (evidence or [])],
        }

    except Exception as exc:
        logger.warning(f"Conversational chat error: {exc}. Using fallback.")
        ans = _generate_fallback_chat_answer(message, farm_context, contradiction_flag, lang, evidence)
        history.add_user_message(message)
        history.add_ai_message(ans)
        return {
            "answer": f"{ans}\n\n[Service notice: {exc}]",
            "contradiction_flag": contradiction_flag,
            "evidence": [e.model_dump() for e in (evidence or [])],
        }


def _build_deterministic_fallback(
    deficiencies: List[Deficiency],
    crop_scores: List[CropScore],
    fertilizer_options: List[FertilizerOption],
    application_window: Optional[ApplicationWindow],
    contradictions: List[str],
    language: str = "en",
) -> str:
    lang = i18n.normalize_language(language)
    parts = []

    low = [d for d in deficiencies if d.status == "LOW"]
    if low:
        names = ", ".join(i18n.nutrient_name(lang, d.nutrient) for d in low)
        parts.append(i18n.phrase(lang, "low_nutrients", nutrients=names))
    else:
        parts.append(i18n.phrase(lang, "no_deficiency"))

    if crop_scores:
        top = crop_scores[0]
        parts.append(i18n.phrase(lang, "crop_score", crop=top.name, score=top.score))

    if fertilizer_options:
        first = fertilizer_options[0]
        type_label = i18n.fertilizer_type_label(lang, first.type)
        parts.append(i18n.phrase(lang, "consider", name=first.name, type=type_label, notes=first.application_notes))

    if application_window:
        if application_window.apply_today == "GO":
            parts.append(i18n.phrase(lang, "apply_today_ok"))
        else:
            parts.append(i18n.phrase(lang, "apply_today_wait", reason=application_window.reason))
            if application_window.next_window:
                parts.append(i18n.phrase(lang, "next_window", date=application_window.next_window))

    if contradictions:
        parts.append(" ".join(contradictions))

    parts.append(i18n.phrase(lang, "no_key_note"))
    if lang != "en":
        parts.append(i18n.PHRASES["en"]["no_key_note"])

    return " ".join(parts)


def _generate_fallback_chat_answer(
    message: str,
    farm_context: str,
    contradiction_flag: Optional[str],
    lang: str,
    evidence: Optional[List[Evidence]] = None,
) -> str:
    """Provides a helpful grounded answer when no LLM key is configured."""
    q = message.lower()
    paragraphs = []

    if contradiction_flag:
        paragraphs.append(f"⚠ Alert: {contradiction_flag}")

    # Helper: extract section lines from farm_context
    def extract_section(header: str) -> List[str]:
        lines = []
        capturing = False
        for line in farm_context.splitlines():
            if header in line:
                capturing = True
                continue
            if capturing:
                if line.isupper() and ":" in line and not line.startswith(" "):
                    break
                if line.strip():
                    lines.append(line.strip())
        return lines

    crop_lines = extract_section("CROP SUITABILITY SCORES")
    fert_lines = extract_section("RECOMMENDED FERTILIZERS")
    deficiency_lines = extract_section("NUTRIENT STATUS CLASSIFICATION")
    weather_lines = extract_section("LIVE WEATHER & APPLICATION WINDOW")

    # 1. Weather / Spray questions
    if any(k in q for k in ["spray", "weather", "evening", "morning", "rain", "window", "wind"]):
        paragraphs.append("Weather & Spray Window Evaluation:")
        if weather_lines:
            for w in weather_lines[:4]:
                paragraphs.append(f"• {w.lstrip('-• ')}")
            paragraphs.append("Foliar Spray Rule: Do not spray if wind exceeds 15 km/h, temperatures exceed 32°C, or rainfall is expected within 3-4 hours.")
        else:
            paragraphs.append("No live weather data provided. Please specify your location to evaluate current temperature, wind speed, and spray feasibility.")

    # 2. Deficiencies / Soil parameters
    elif any(k in q for k in ["deficiency", "deficiencies", "low nutrient", "soil health"]):
        low_items = [d for d in deficiency_lines if "LOW" in d or "DEFICIENT" in d]
        if low_items:
            paragraphs.append("Identified Soil Deficiencies:")
            for item in low_items:
                paragraphs.append(f"• {item.lstrip('-• ')}")
            paragraphs.append("These nutrients are below critical agricultural thresholds and should be addressed through basal or foliar applications.")
        elif deficiency_lines:
            paragraphs.append("Nutrient Status Summary:")
            for d in deficiency_lines[:5]:
                paragraphs.append(f"• {d.lstrip('-• ')}")
            paragraphs.append("No critical deficiencies detected; maintain balanced replenishment.")
        else:
            paragraphs.append("Upload a valid soil report to detect specific nutrient deficiencies.")

    # 3. Organic fertilizers / Organic carbon
    elif any(k in q for k in ["organic", "carbon", "fym", "vermicompost", "manure"]):
        organic_options = [f for f in fert_lines if "[ORGANIC]" in f.upper()]
        paragraphs.append("Organic Fertilizer & Soil Health Recommendations:")
        if organic_options:
            for opt in organic_options:
                paragraphs.append(f"• {opt.lstrip('-• ')}")
        else:
            paragraphs.append("• Well-rotted Farmyard Manure (FYM): Apply 10–12 tonnes/ha during land preparation.")
            paragraphs.append("• Vermicompost: Apply 2–3 tonnes/ha for rapid microbial activity and moisture retention.")
            paragraphs.append("• Green Manuring: Sow Dhaincha or Sunnhemp and incorporate into the soil after 45 days.")
        paragraphs.append("Improving organic carbon enhances nutrient retention, microbial diversity, and reduces fertilizer leaching.")

    # 4. Which fertilizer / alternative fertilizer
    elif any(k in q for k in ["fertilizer", "urea", "dap", "ssp", "mop", "alternative", "npk"]):
        if "alternative" in q:
            paragraphs.append("Alternative Fertilizer Options:")
            paragraphs.append("• Instead of DAP (18-46-0): Use Single Super Phosphate (SSP 16% P2O5 + 11% Sulphur) combined with Urea for nitrogen.")
            paragraphs.append("• Instead of MOP (Muriate of Potash): Sulphate of Potash (SOP) is recommended, especially in saline or high-chloride soils.")
            paragraphs.append("• For organic substitution: Replace chemical nitrogen with vermicompost and Azotobacter/Rhizobium biofertilizer.")
        elif fert_lines:
            paragraphs.append("Recommended Fertilizer Schedule:")
            for f in fert_lines[:5]:
                paragraphs.append(f"• {f.lstrip('-• ')}")
        else:
            paragraphs.append("Fertilizer recommendations are generated based on your soil test deficiencies.")

    # 5. Which crop / Crop suitability / Is [Crop] suitable
    elif any(k in q for k in ["crop", "grow", "suitable", "suitability", "score"]):
        found_crop_line = None
        for c_line in crop_lines:
            crop_name = c_line.split(":")[0].replace("-", "").strip()
            if crop_name.lower() in q:
                found_crop_line = c_line
                break

        if found_crop_line:
            paragraphs.append(f"Crop Evaluation: {found_crop_line.lstrip('-• ')}")
            paragraphs.append("Recommendation: Ensure soil pH and major nutrients align with this crop's requirements.")
        elif crop_lines:
            paragraphs.append("Top Suited Crops for Your Soil (Deterministic Ranking):")
            for c in crop_lines[:5]:
                paragraphs.append(f"• {c.lstrip('-• ')}")
        else:
            paragraphs.append("Crop suitability scoring requires your soil report parameters. Please provide soil test data.")

    # 6. Why questions / Knowledge & RAG evidence (e.g., Why is nitrogen low?)
    elif any(k in q for k in ["why", "how", "reason"]):
        paragraphs.append("Agronomic Scientific Explanation:")
        if evidence:
            for ev in evidence[:2]:
                paragraphs.append(f"• [{ev.source}]: {ev.text[:220]}...")
        else:
            if "nitrogen" in q:
                paragraphs.append("Nitrogen is highly mobile in soil. In light-textured soils or soils with low organic carbon (< 0.5%), nitrogen is readily lost through nitrate leaching beyond the root zone or volatilization as ammonia gas. Split applications and organic matter additions prevent these losses.")
            elif "carbon" in q:
                paragraphs.append("Soil Organic Carbon (SOC) depletes quickly in warm tropical climates due to rapid microbial oxidation and intensive tillage. Regular incorporation of crop residues, FYM, and cover crops restores SOC.")
            else:
                paragraphs.append("Soil nutrient availability is governed by pH, moisture, and organic matter interactions.")

    # 7. What should I do next / general plan
    elif any(k in q for k in ["next", "plan", "steps", "guide", "do next"]):
        paragraphs.append("Recommended Action Plan for Your Farm:")
        paragraphs.append("1. Correct Low Nutrients: Prioritize basal application of required fertilizers or organic manure during land prep.")
        paragraphs.append("2. Select Suitable Crop: Choose one of the top-ranked crops matching your soil characteristics and season.")
        paragraphs.append("3. Monitor Spray Windows: Time any foliar applications during calm morning (06:00-09:00) or evening (16:00-18:30) periods.")
        paragraphs.append("4. Incorporate organic matter to sustain long-term soil health.")

    else:
        paragraphs.append("Farm Advisory Summary:")
        if deficiency_lines:
            low_items = [d for d in deficiency_lines if "LOW" in d]
            if low_items:
                paragraphs.append(f"Key deficiency to address: {low_items[0].lstrip('-• ')}")
        if crop_lines:
            paragraphs.append(f"Top crop match: {crop_lines[0].lstrip('-• ')}")
        if fert_lines:
            paragraphs.append(f"Top fertilizer recommendation: {fert_lines[0].lstrip('-• ')}")

    return "\n\n".join(paragraphs)
