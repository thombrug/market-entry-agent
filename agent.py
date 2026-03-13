"""Core agent logic: Gemini API call and post-call EAS recomputation."""
from __future__ import annotations
import os
from google import genai
from google.genai import types
from schema import EntryAnalysisInput, EntryScorecard, EntryScorecardLLMOutput, Verdict
from prompts import SYSTEM_PROMPT, build_user_prompt


def run_entry_analysis(entry_input: EntryAnalysisInput) -> EntryScorecard:
    """Run market entry analysis using Gemini with structured output.

    Makes a single API call with response_schema=EntryScorecardLLMOutput,
    then deterministically computes EAS and verdict post-call.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it before running the agent."
        )
    client = genai.Client(api_key=api_key)

    user_prompt = build_user_prompt(entry_input.model_dump())

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(role="user", parts=[types.Part(text=user_prompt)])
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=EntryScorecardLLMOutput,
        ),
    )

    llm_output: EntryScorecardLLMOutput = response.parsed

    if llm_output is None:
        raise ValueError(
            f"Gemini returned no parsed output. "
            f"finish_reason={response.candidates[0].finish_reason if response.candidates else 'unknown'}"
        )

    # Promote to EntryScorecard with placeholder values (overwritten by _recompute_scorecard)
    scorecard = EntryScorecard(
        **llm_output.model_dump(),
        entry_attractiveness_score=0.0,
        verdict=Verdict.CONDITIONAL,
    )

    return _recompute_scorecard(scorecard)


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
