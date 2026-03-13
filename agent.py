"""Core agent logic: Gemini API call and post-call EAS recomputation."""
from __future__ import annotations

from schema import EntryScorecard, Verdict


def _recompute_scorecard(scorecard: EntryScorecard) -> EntryScorecard:
    """Recompute EAS and verdict deterministically from dimension scores.

    Formula (normalized 0-100):
        weighted_avg = Σ(weight_i × score_i)
        EAS = 100 × (1 − (weighted_avg − 1) / 4)

    Maps: all scores=1 → EAS=100 (best case), all scores=5 → EAS=0 (worst case).

    Verdict thresholds:
        EAS ≥ 65 → Attractive Entry
        EAS 45–64 → Conditional Entry
        EAS < 45 → Avoid Entry
    """
    weighted_avg = sum(d.weight * d.score for d in scorecard.dimensions)
    eas = round(100.0 * (1.0 - (weighted_avg - 1.0) / 4.0), 1)
    if eas >= 65.0:
        verdict = Verdict.ATTRACTIVE
    elif eas >= 45.0:
        verdict = Verdict.CONDITIONAL
    else:
        verdict = Verdict.AVOID
    return scorecard.model_copy(update={
        "entry_attractiveness_score": eas,
        "verdict": verdict,
    })
