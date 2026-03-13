"""Pydantic models for the Market Entry Attractiveness Agent."""
from __future__ import annotations

import math
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared enum
# ---------------------------------------------------------------------------

class StrengthLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class IncumbentProfile(BaseModel):
    name: str
    estimated_market_share: float   # 0.0–1.0
    financial_strength: StrengthLevel
    retaliation_history: StrengthLevel

    @field_validator("estimated_market_share")
    @classmethod
    def validate_market_share(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"estimated_market_share must be between 0.0 and 1.0, got {v}"
            )
        return v


class MarketData(BaseModel):
    estimated_size_usd: int
    annual_growth_rate: float
    hhi: int  # Herfindahl-Hirschman Index 0–10000

    @field_validator("hhi")
    @classmethod
    def validate_hhi(cls, v: int) -> int:
        if not 0 <= v <= 10_000:
            raise ValueError(f"hhi must be between 0 and 10000, got {v}")
        return v


class BarrierSignals(BaseModel):
    capital_requirement_usd: int
    regulatory_complexity: StrengthLevel
    switching_costs: StrengthLevel
    network_effects: StrengthLevel


class EntryAnalysisInput(BaseModel):
    market_name: str
    entrant_description: str
    incumbents: list[IncumbentProfile]
    market_data: MarketData
    barrier_signals: BarrierSignals
    entrant_strengths: list[str]

    @model_validator(mode="after")
    def validate_incumbents_not_empty(self) -> "EntryAnalysisInput":
        if len(self.incumbents) < 1:
            raise ValueError("incumbents must contain at least one entry")
        return self


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class DimensionScore(BaseModel):
    name: str
    score: int       # 1–5: 1=highly favorable for entrant, 5=highly unfavorable
    weight: float    # 0.0–1.0; all 6 weights sum to 1.0
    key_factors: list[str]
    evidence: str
    # weighted_score is intentionally excluded — computed post-call to avoid LLM arithmetic errors

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError(f"score must be between 1 and 5, got {v}")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"weight must be between 0.0 and 1.0, got {v}")
        return v


class Verdict(str, Enum):
    ATTRACTIVE = "Attractive Entry"
    CONDITIONAL = "Conditional Entry"
    AVOID = "Avoid Entry"


class EntryScorecardLLMOutput(BaseModel):
    """Fields produced by the LLM via response_schema. EAS and verdict excluded — computed post-call."""
    market_name: str
    dimensions: Annotated[list[DimensionScore], Field(min_length=6, max_length=6)]  # exactly 6 dimensions
    confidence: StrengthLevel
    critical_risks: list[str]
    strategic_recommendation: str
    suggested_entry_mode: str

    @model_validator(mode="after")
    def validate_weights_sum_to_one(self) -> "EntryScorecardLLMOutput":
        if self.dimensions:
            total = sum(d.weight for d in self.dimensions)
            if not math.isclose(total, 1.0, abs_tol=1e-6):
                raise ValueError(f"dimension weights must sum to 1.0, got {total:.6f}")
        return self


class EntryScorecard(EntryScorecardLLMOutput):
    """Full output model. Extends LLM output with deterministically computed EAS, verdict, and HTML."""
    entry_attractiveness_score: float  # 0–100; set by _recompute_scorecard in agent.py
    verdict: Verdict                   # set by _recompute_scorecard from EAS thresholds
    html_report: str | None = None     # injected by renderer.py; None when --json-only
