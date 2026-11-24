"""Structured representations of a soil report."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class SoilValue(BaseModel):
    value: float
    unit: Optional[str] = None


class SoilReport(BaseModel):
    """Structured soil data extracted from a Soil Health Card / lab report.

    All fields are optional because real-world reports are frequently
    incomplete. Missing fields should lower confidence downstream rather
    than being silently defaulted.
    """

    nitrogen: Optional[SoilValue] = None          # kg/ha
    phosphorus: Optional[SoilValue] = None         # kg/ha
    potassium: Optional[SoilValue] = None          # kg/ha
    ph: Optional[SoilValue] = None
    organic_carbon: Optional[SoilValue] = None     # %
    electrical_conductivity: Optional[SoilValue] = None  # dS/m
    zinc: Optional[SoilValue] = None               # ppm
    iron: Optional[SoilValue] = None               # ppm
    boron: Optional[SoilValue] = None              # ppm
    sulphur: Optional[SoilValue] = None            # ppm

    raw_text_excerpt: Optional[str] = None
    extraction_warnings: list[str] = Field(default_factory=list)

    def completeness(self) -> float:
        """Fraction of the core fields (N,P,K,pH,OC,EC) that were found."""
        core = [
            self.nitrogen,
            self.phosphorus,
            self.potassium,
            self.ph,
            self.organic_carbon,
            self.electrical_conductivity,
        ]
        found = sum(1 for f in core if f is not None)
        return round(found / len(core), 2)
