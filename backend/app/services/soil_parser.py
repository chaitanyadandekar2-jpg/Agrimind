"""Converts raw soil-report text into a structured SoilReport.

Soil Health Cards and private lab reports vary a lot in formatting, so
each parameter is matched with several tolerant regex patterns. This is
intentionally deterministic (no LLM) per the project's engineering
principle: the LLM should not be responsible for numeric extraction that
downstream calculations depend on.
"""
from __future__ import annotations

import re
from app.models.soil import SoilReport, SoilValue

def _full_name_pattern(full_name: str, abbrev: str, units: str) -> str:
    """Build a tolerant pattern for '<Full Name> [(ABBR)] [:/-] <value> [unit]'.

    IMPORTANT: the abbreviation group is wrapped as `(?:\\(?abbr\\)?)?` so the
    ENTIRE "(ABBR)" chunk is optional -- not just the parentheses around a
    mandatory abbreviation. A previous version wrote this as `\\(?abbr\\)?`,
    which makes the parentheses optional but still requires the literal
    abbreviation letters to appear in the text. That silently failed to
    match reports that write "Organic Carbon: 0.45%" without "(OC)" next
    to it, producing an UNKNOWN status even though the value was present.
    """
    return (
        rf"{full_name}\s*(?:\(?{abbrev}\)?)?\s*[:\-]?\s*"
        rf"(?P<value>\d+\.?\d*)\s*(?P<unit>{units})?"
    )


def _abbrev_pattern(abbrev: str, units: str) -> str:
    """Fallback pattern matching just the standalone abbreviation, e.g. 'N: 180'."""
    return rf"\b{abbrev}\b\s*[:\-]?\s*(?P<value>\d+\.?\d*)\s*(?P<unit>{units})?"


_KG_HA = r"kg/ha|kg\s*/\s*ha|ppm"
_PPM = r"ppm"
_PCT = r"%"
_DS_M = r"ds/m|dS/m|mmhos/cm"

# Each entry: field_name -> list of regex patterns, tried in order.
# Patterns capture (value) and optionally (unit) as named groups.
_PATTERNS: dict[str, list[str]] = {
    "nitrogen": [
        r"(?:available\s+)?" + _full_name_pattern("nitrogen", "n", _KG_HA),
        _abbrev_pattern("N", _KG_HA),
    ],
    "phosphorus": [
        r"(?:available\s+)?" + _full_name_pattern("phosphorus", "p", _KG_HA),
        _abbrev_pattern("P", _KG_HA),
    ],
    "potassium": [
        r"(?:available\s+)?" + _full_name_pattern("potassium", "k", _KG_HA),
        _abbrev_pattern("K", _KG_HA),
    ],
    "ph": [
        r"\bpH\b(?:\s*\(1:2\))?\s*[:\-]?\s*(?P<value>\d+\.?\d*)",
    ],
    "organic_carbon": [
        _full_name_pattern(r"organic\s+carbon", "oc", _PCT),
        _abbrev_pattern("OC", _PCT),
    ],
    "electrical_conductivity": [
        _full_name_pattern(r"electrical\s+conductivity", "ec", _DS_M),
        _abbrev_pattern("EC", _DS_M),
    ],
    "zinc": [_full_name_pattern("zinc", "zn", _PPM), _abbrev_pattern("Zn", _PPM)],
    "iron": [_full_name_pattern("iron", "fe", _PPM), _abbrev_pattern("Fe", _PPM)],
    "boron": [_full_name_pattern("boron", "b", _PPM), _abbrev_pattern("B", _PPM)],
    "sulphur": [_full_name_pattern(r"sulph?ur", "s", _PPM), _abbrev_pattern("S", _PPM)],
}

# Only these six affect the deterministic recommendation engine directly;
# missing micronutrients shouldn't clutter the UI with warnings.
_CORE_FIELDS = {
    "nitrogen",
    "phosphorus",
    "potassium",
    "ph",
    "organic_carbon",
    "electrical_conductivity",
}

_DEFAULT_UNITS = {
    "nitrogen": "kg/ha",
    "phosphorus": "kg/ha",
    "potassium": "kg/ha",
    "organic_carbon": "%",
    "electrical_conductivity": "dS/m",
    "zinc": "ppm",
    "iron": "ppm",
    "boron": "ppm",
    "sulphur": "ppm",
}


def parse_soil_text(text: str) -> SoilReport:
    warnings: list[str] = []
    fields: dict[str, SoilValue] = {}
    lower_text = text

    for field, patterns in _PATTERNS.items():
        found = False
        for pattern in patterns:
            match = re.search(pattern, lower_text, flags=re.IGNORECASE)
            if match:
                try:
                    value = float(match.group("value"))
                except (ValueError, IndexError):
                    continue
                unit = None
                if "unit" in match.groupdict():
                    unit = match.group("unit")
                unit = unit or _DEFAULT_UNITS.get(field)
                fields[field] = SoilValue(value=value, unit=unit)
                found = True
                break
        if not found and field in _CORE_FIELDS:
            warnings.append(f"Could not find a value for '{field}' in the uploaded report.")

    report = SoilReport(
        **fields,
        raw_text_excerpt=text[:800],
        extraction_warnings=warnings,
    )
    return report
