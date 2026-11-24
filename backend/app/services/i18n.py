"""Language support for AgriMind's natural-language layer only.

Deliberately scoped: structured API fields (nutrient keys, status codes like
LOW/MEDIUM/HIGH, deficiency.nutrient, etc.) stay in English always -- that's
the stable contract the frontend and any other client code already relies
on. Only the free-text explanation (LLM output, and the no-API-key template
fallback) is produced in the requested language. This keeps the rest of the
project unchanged while making the actual farmer-facing explanation
multilingual.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "hi", "mr")
DEFAULT_LANGUAGE = "en"

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    lang = language.strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def llm_language_instruction(language: str) -> str:
    """Appended to the LLM system prompt so the model answers in the
    requested language. The model is instructed to keep nutrient
    abbreviations (N, P, K) recognizable even in Devanagari text, since
    farmers and extension workers commonly read those as-is.
    """
    lang = normalize_language(language)
    if lang == "en":
        return "Respond in clear, plain English."
    name = LANGUAGE_NAMES[lang]
    return (
        f"Respond entirely in {name}, written in Devanagari script, in a natural, "
        f"conversational tone a farmer would actually read. When you mention a nutrient, "
        f"give the common {name} agricultural term followed by its English abbreviation in "
        f"parentheses the first time it's used (e.g. for nitrogen), so it stays recognizable. "
        f"Keep product/fertilizer names (like Urea, DAP, ZnSO4) in Latin script since that's "
        f"how farmers see them on packaging."
    )


# ---------------------------------------------------------------------------
# Template-fallback phrase dictionary, used only when no LLM key is
# configured. Intentionally minimal -- covers the fixed sentence structure
# in llm_service._template_fallback(), not arbitrary free text. Fertilizer
# names/application notes stay in English in all languages, since they come
# from a single-source-of-truth knowledge base that isn't (yet) translated,
# and mistranslating a dosage/product name is worse than leaving it in
# English.
# ---------------------------------------------------------------------------

NUTRIENT_NAMES = {
    "en": {
        "nitrogen": "nitrogen", "phosphorus": "phosphorus", "potassium": "potassium",
        "organic_carbon": "organic carbon", "zinc": "zinc", "iron": "iron", "sulphur": "sulphur",
    },
    "hi": {
        "nitrogen": "नाइट्रोजन (N)", "phosphorus": "फास्फोरस (P)", "potassium": "पोटैशियम (K)",
        "organic_carbon": "जैविक कार्बन (OC)", "zinc": "जिंक (Zn)", "iron": "आयरन (Fe)",
        "sulphur": "सल्फर (S)",
    },
    "mr": {
        "nitrogen": "नत्र (N)", "phosphorus": "स्फुरद (P)", "potassium": "पालाश (K)",
        "organic_carbon": "सेंद्रिय कर्ब (OC)", "zinc": "जस्त (Zn)", "iron": "लोह (Fe)",
        "sulphur": "गंधक (S)",
    },
}

PHRASES = {
    "en": {
        "low_nutrients": "Your soil is currently low in {nutrients}.",
        "no_deficiency": "No major nutrient deficiencies were detected from your report.",
        "crop_score": "{crop} scores {score}/100 for suitability based on your soil data.",
        "consider": "Consider {name} ({type}) - {notes}",
        "apply_today_ok": "Current weather conditions look suitable to apply today.",
        "apply_today_wait": "Hold off on applying: {reason}",
        "next_window": "Next suitable window looks like {date}.",
        "no_key_note": "(Set OPENAI_API_KEY in .env for a more natural, conversational explanation.)",
        "type_organic": "organic",
        "type_chemical": "chemical",
    },
    "hi": {
        "low_nutrients": "आपकी मिट्टी में फिलहाल {nutrients} की कमी है।",
        "no_deficiency": "आपकी रिपोर्ट में कोई बड़ी पोषक तत्व की कमी नहीं पाई गई।",
        "crop_score": "आपकी मिट्टी के आंकड़ों के अनुसार {crop} की उपयुक्तता {score}/100 है।",
        "consider": "{name} ({type}) का उपयोग करें - {notes}",
        "apply_today_ok": "आज का मौसम आवेदन के लिए उपयुक्त लग रहा है।",
        "apply_today_wait": "अभी आवेदन न करें: {reason}",
        "next_window": "अगला उपयुक्त समय लगभग {date} को हो सकता है।",
        "no_key_note": "(अधिक स्वाभाविक, बातचीत जैसी व्याख्या के लिए .env में OPENAI_API_KEY सेट करें।)",
        "type_organic": "जैविक",
        "type_chemical": "रासायनिक",
    },
    "mr": {
        "low_nutrients": "तुमच्या मातीत सध्या {nutrients} ची कमतरता आहे.",
        "no_deficiency": "तुमच्या अहवालात कोणतीही मोठी पोषक तत्वांची कमतरता आढळली नाही.",
        "crop_score": "तुमच्या मातीच्या माहितीनुसार {crop} ची योग्यता {score}/100 आहे.",
        "consider": "{name} ({type}) वापरण्याचा विचार करा - {notes}",
        "apply_today_ok": "आजचे हवामान वापरण्यासाठी योग्य दिसत आहे.",
        "apply_today_wait": "आत्ता वापर टाळा: {reason}",
        "next_window": "पुढील योग्य वेळ अंदाजे {date} असू शकते.",
        "no_key_note": "(अधिक नैसर्गिक, संवादात्मक स्पष्टीकरणासाठी .env मध्ये OPENAI_API_KEY सेट करा.)",
        "type_organic": "सेंद्रिय",
        "type_chemical": "रासायनिक",
    },
}


def phrase(language: str, key: str, **kwargs) -> str:
    lang = normalize_language(language)
    template = PHRASES[lang].get(key, PHRASES["en"][key])
    return template.format(**kwargs)


def nutrient_name(language: str, nutrient_key: str) -> str:
    lang = normalize_language(language)
    return NUTRIENT_NAMES[lang].get(nutrient_key, nutrient_key.replace("_", " "))


def fertilizer_type_label(language: str, ftype: str) -> str:
    lang = normalize_language(language)
    key = "type_organic" if ftype == "organic" else "type_chemical"
    return PHRASES[lang][key]
