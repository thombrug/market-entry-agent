"""Unit tests for market-entry-agent."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dims(score: int, n: int = 5) -> list:
    """Create n DimensionScore objects with equal weight (summing to 1.0) and uniform score."""
    from schema import DimensionScore
    weight = round(1.0 / n, 10)
    return [
        DimensionScore(name=f"Dim{i+1}", score=score, weight=weight,
                       key_factors=["test factor"], evidence="test evidence")
        for i in range(n)
    ]


def _make_dims_custom(scores_weights: list[tuple[int, float]]) -> list:
    """Create DimensionScore objects from (score, weight) pairs."""
    from schema import DimensionScore
    return [
        DimensionScore(name=f"Dim{i+1}", score=s, weight=w,
                       key_factors=[f"factor {i}"], evidence=f"evidence {i}")
        for i, (s, w) in enumerate(scores_weights)
    ]


def _base_scorecard(dimensions):
    """Build a minimal EntryScorecard with placeholder EAS/verdict."""
    from schema import EntryScorecard, StrengthLevel, Verdict
    return EntryScorecard(
        market_name="Test Market",
        dimensions=dimensions,
        confidence=StrengthLevel.MEDIUM,
        critical_risks=["test risk"],
        strategic_recommendation="Test recommendation.",
        suggested_entry_mode="niche differentiation",
        entry_attractiveness_score=0.0,
        verdict=Verdict.CONDITIONAL,
    )


# ---------------------------------------------------------------------------
# TestInputSchemaValidation
# ---------------------------------------------------------------------------

class TestInputSchemaValidation:

    def test_valid_full_input(self):
        from schema import (EntryAnalysisInput, IncumbentProfile, MarketData,
                            BarrierSignals, StrengthLevel)
        inp = EntryAnalysisInput(
            market_name="EV Charging — Germany",
            entrant_description="A startup with $50M funding.",
            incumbents=[
                IncumbentProfile(name="Ionity", estimated_market_share=0.35,
                                 financial_strength=StrengthLevel.HIGH,
                                 retaliation_history=StrengthLevel.MEDIUM)
            ],
            market_data=MarketData(estimated_size_usd=2_000_000_000,
                                   annual_growth_rate=0.28, hhi=2800),
            barrier_signals=BarrierSignals(capital_requirement_usd=25_000_000,
                                           regulatory_complexity=StrengthLevel.HIGH,
                                           switching_costs=StrengthLevel.LOW,
                                           network_effects=StrengthLevel.MEDIUM),
            entrant_strengths=["proprietary tech", "strong balance sheet"],
        )
        assert inp.market_name == "EV Charging — Germany"
        assert len(inp.incumbents) == 1

    def test_hhi_above_10000_raises(self):
        from schema import MarketData
        with pytest.raises(ValidationError):
            MarketData(estimated_size_usd=1_000_000, annual_growth_rate=0.1, hhi=10_001)

    def test_hhi_below_zero_raises(self):
        from schema import MarketData
        with pytest.raises(ValidationError):
            MarketData(estimated_size_usd=1_000_000, annual_growth_rate=0.1, hhi=-1)

    def test_market_share_above_one_raises(self):
        from schema import IncumbentProfile, StrengthLevel
        with pytest.raises(ValidationError):
            IncumbentProfile(name="BigCo", estimated_market_share=1.1,
                             financial_strength=StrengthLevel.HIGH,
                             retaliation_history=StrengthLevel.LOW)

    def test_market_share_below_zero_raises(self):
        from schema import IncumbentProfile, StrengthLevel
        with pytest.raises(ValidationError):
            IncumbentProfile(name="BigCo", estimated_market_share=-0.1,
                             financial_strength=StrengthLevel.HIGH,
                             retaliation_history=StrengthLevel.LOW)

    def test_empty_incumbents_raises(self):
        from schema import (EntryAnalysisInput, MarketData, BarrierSignals,
                            StrengthLevel)
        with pytest.raises(ValidationError):
            EntryAnalysisInput(
                market_name="Test",
                entrant_description="Test entrant",
                incumbents=[],
                market_data=MarketData(estimated_size_usd=1_000_000,
                                       annual_growth_rate=0.1, hhi=2500),
                barrier_signals=BarrierSignals(capital_requirement_usd=5_000_000,
                                               regulatory_complexity=StrengthLevel.MEDIUM,
                                               switching_costs=StrengthLevel.LOW,
                                               network_effects=StrengthLevel.LOW),
                entrant_strengths=["tech"],
            )


# ---------------------------------------------------------------------------
# TestEASFormula
# ---------------------------------------------------------------------------

class TestEASFormula:

    def test_all_scores_one_gives_eas_100(self):
        from agent import _recompute_scorecard
        result = _recompute_scorecard(_base_scorecard(_make_dims(1)))
        assert result.entry_attractiveness_score == 100.0

    def test_all_scores_five_gives_eas_zero(self):
        from agent import _recompute_scorecard
        result = _recompute_scorecard(_base_scorecard(_make_dims(5)))
        assert result.entry_attractiveness_score == 0.0

    def test_all_scores_three_gives_eas_50(self):
        from agent import _recompute_scorecard
        result = _recompute_scorecard(_base_scorecard(_make_dims(3)))
        assert result.entry_attractiveness_score == 50.0

    def test_weighted_avg_2_4_gives_eas_65(self):
        """EAS boundary: wa=2.4 → EAS=65. Use 5 dims w=0.2, scores [2,2,2,3,3]."""
        from agent import _recompute_scorecard
        dims = _make_dims_custom([(2, 0.2), (2, 0.2), (2, 0.2), (3, 0.2), (3, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.entry_attractiveness_score == 65.0

    def test_weighted_avg_3_2_gives_eas_45(self):
        """EAS boundary: wa=3.2 → EAS=45. Use 5 dims w=0.2, scores [3,3,3,3,4]."""
        from agent import _recompute_scorecard
        dims = _make_dims_custom([(3, 0.2), (3, 0.2), (3, 0.2), (3, 0.2), (4, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.entry_attractiveness_score == 45.0


# ---------------------------------------------------------------------------
# TestVerdictThresholds
# ---------------------------------------------------------------------------

class TestVerdictThresholds:

    def test_eas_100_is_attractive(self):
        from agent import _recompute_scorecard
        from schema import Verdict
        result = _recompute_scorecard(_base_scorecard(_make_dims(1)))
        assert result.verdict == Verdict.ATTRACTIVE

    def test_eas_65_is_attractive(self):
        """wa=2.4 → EAS=65 → exactly on ATTRACTIVE boundary."""
        from agent import _recompute_scorecard
        from schema import Verdict
        dims = _make_dims_custom([(2, 0.2), (2, 0.2), (2, 0.2), (3, 0.2), (3, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.verdict == Verdict.ATTRACTIVE

    def test_eas_64_is_conditional(self):
        """wa just above 2.4 → EAS slightly below 65 → CONDITIONAL.
        Use scores [2,2,3,3,3] w=0.2 → wa=2.6 → EAS=60."""
        from agent import _recompute_scorecard
        from schema import Verdict
        dims = _make_dims_custom([(2, 0.2), (2, 0.2), (3, 0.2), (3, 0.2), (3, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.verdict == Verdict.CONDITIONAL

    def test_eas_45_is_conditional(self):
        """wa=3.2 → EAS=45 → exactly on lower CONDITIONAL boundary."""
        from agent import _recompute_scorecard
        from schema import Verdict
        dims = _make_dims_custom([(3, 0.2), (3, 0.2), (3, 0.2), (3, 0.2), (4, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.verdict == Verdict.CONDITIONAL

    def test_eas_below_45_is_avoid(self):
        """wa=3.4 → EAS=40 → AVOID. Scores [3,3,3,4,4] w=0.2 → wa=3.4."""
        from agent import _recompute_scorecard
        from schema import Verdict
        dims = _make_dims_custom([(3, 0.2), (3, 0.2), (3, 0.2), (4, 0.2), (4, 0.2)])
        result = _recompute_scorecard(_base_scorecard(dims))
        assert result.verdict == Verdict.AVOID

    def test_eas_zero_is_avoid(self):
        from agent import _recompute_scorecard
        from schema import Verdict
        result = _recompute_scorecard(_base_scorecard(_make_dims(5)))
        assert result.verdict == Verdict.AVOID
