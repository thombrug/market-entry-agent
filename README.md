# Market Entry Attractiveness Agent

A market entry analysis agent grounded in Porter's Five Forces framework and Bain's
barriers-to-entry taxonomy. Given a structured description of a market, entrant, and
incumbents, it returns a quantified **Entry Attractiveness Score (EAS, 0–100)** with
per-dimension breakdown, verdict, and strategic recommendation.

Built with the **Google Gemini SDK** (`google-genai`) using structured output via
`response_schema` — designed to be called by orchestrator agents.

---

## Scientific Basis

| Reference | Contribution |
|---|---|
| **Porter, M.E. (2008).** "The Five Competitive Forces That Shape Strategy." *HBR*, 86(1). | Five structural dimensions defining industry attractiveness |
| **Bain, J.S. (1956).** *Barriers to New Competition.* Harvard University Press. | Barriers taxonomy: capital requirements, scale economies, product differentiation |
| **McAfee, R.P., Mialon, H.M., & Williams, M.A. (2004).** "What Is a Barrier to Entry?" *AER*, 94(2), 461–465. DOI: [10.1257/0002828041302235](https://doi.org/10.1257/0002828041302235) | Formal economic definition and measurement of entry barriers |

---

## Architecture

```
EntryAnalysisInput (JSON)
         │
         ▼
    agent.py: run_entry_analysis()
         │
         ├── Validate → Pydantic EntryAnalysisInput
         ├── Build system prompt (Porter/Bain framework)
         ▼
    Gemini API (gemini-2.0-flash)
    response_schema=EntryScorecardLLMOutput   ← typed structured output
         │
         ▼
    response.parsed → EntryScorecardLLMOutput
         │
         ├── _recompute_scorecard() → EAS + verdict (deterministic, not LLM-computed)
         └── Return EntryScorecard
```

**Six dimensions (Porter + Bain):**

| Dimension | Weight | Source |
|---|---|---|
| Barriers to Entry | 30% | Bain (1956); McAfee et al. (2004) |
| Incumbent Retaliation Risk | 25% | Caves & Porter (1977) |
| Market Attractiveness | 20% | Porter (2008) |
| Competitive Rivalry | 15% | Porter (2008) |
| Buyer Power | 5% | Porter (2008) |
| Supplier Power | 5% | Porter (2008) |

**EAS formula:** `EAS = 100 × (1 − (Σ(weight × score) − 1) / 4)`

Scores 1–5: 1 = highly favorable for entrant, 5 = highly unfavorable.
Verdicts: EAS ≥ 65 → Attractive Entry, 45–64 → Conditional Entry, < 45 → Avoid Entry.

---

## Project Structure

```
market-entry-agent/
├── agent.yaml          # Platform manifest
├── schema.py           # All Pydantic models (input + output)
├── prompts.py          # System prompt with Porter/Bain framework
├── agent.py            # Gemini call + _recompute_scorecard()
├── renderer.py         # Jinja2 HTML report with radar chart
├── template.html       # Self-contained HTML template
├── main.py             # CLI entry point
├── example_input.json  # Built-in example (EV charging, Germany)
└── tests/
    └── test_market_entry.py
```

---

## Installation

```bash
git clone <repo-url>
cd market-entry-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -e .
cp .env.example .env
# Edit .env: set GEMINI_API_KEY=your_key_here
```

---

## Usage

```bash
# Run built-in example (EV charging networks, Germany)
python main.py

# Run with your own input file
python main.py my_market.json

# Pipe JSON from stdin
cat market.json | python main.py

# JSON output only (no HTML report)
python main.py --example --json-only

# Print to stdout, don't write files
python main.py --example --no-save

# Custom output directory
python main.py --example --output-dir ./results
```

Output files written to current directory (or `--output-dir`):
- `entry_output.json` — structured JSON with all scores, EAS, verdict, recommendation
- `entry_report.html` — self-contained HTML with radar chart and dimension breakdown

---

## Input Format

```json
{
  "market_name": "Your Market",
  "entrant_description": "Description of the company entering the market.",
  "incumbents": [
    {
      "name": "Incumbent Name",
      "estimated_market_share": 0.35,
      "financial_strength": "high",
      "retaliation_history": "medium"
    }
  ],
  "market_data": {
    "estimated_size_usd": 2000000000,
    "annual_growth_rate": 0.28,
    "hhi": 2800
  },
  "barrier_signals": {
    "capital_requirement_usd": 25000000,
    "regulatory_complexity": "high",
    "switching_costs": "low",
    "network_effects": "medium"
  },
  "entrant_strengths": ["Proprietary technology", "Strong funding"]
}
```

Valid values for enum fields: `"low"`, `"medium"`, `"high"`.
HHI range: 0 (perfect competition) to 10,000 (monopoly).

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## References

- McAfee, R.P., Mialon, H.M., & Williams, M.A. (2004). What Is a Barrier to Entry? *American Economic Review*, 94(2), 461–465. https://doi.org/10.1257/0002828041302235
- Porter, M.E. (2008). The Five Competitive Forces That Shape Strategy. *Harvard Business Review*, 86(1), 78–93.
- Bain, J.S. (1956). *Barriers to New Competition*. Harvard University Press.
