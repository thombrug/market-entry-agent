#!/usr/bin/env python3
"""Market Entry Attractiveness Agent — CLI entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (silently ignored if absent)
load_dotenv(Path(__file__).parent / ".env")

from schema import EntryAnalysisInput
from agent import run_entry_analysis
from renderer import render_report

_EXAMPLE_INPUT_PATH = Path(__file__).parent / "example_input.json"


def _load_example() -> EntryAnalysisInput:
    with _EXAMPLE_INPUT_PATH.open() as f:
        return EntryAnalysisInput(**json.load(f))


def _load_file(path: str) -> EntryAnalysisInput:
    with open(path) as f:
        return EntryAnalysisInput(**json.load(f))


def _load_stdin() -> EntryAnalysisInput:
    return EntryAnalysisInput(**json.load(sys.stdin))


def _save_outputs(scorecard, output_dir: Path, json_only: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    output_dict = scorecard.model_dump()
    output_dict.pop("html_report", None)

    json_path = output_dir / "entry_output.json"
    json_path.write_text(json.dumps(output_dict, indent=2), encoding="utf-8")
    print(f"JSON saved to {json_path}", file=sys.stderr)

    if not json_only:
        html = render_report(scorecard)
        html_path = output_dir / "entry_report.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"HTML report saved to {html_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Market Entry Attractiveness Agent (Porter Five Forces + Bain)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                             # Run built-in EV charging example
  python main.py input.json                  # Load from a JSON file
  cat input.json | python main.py            # Read from stdin
  python main.py --example --json-only       # JSON output only, no HTML
  python main.py --no-save                   # Print to stdout, don't write files
  python main.py --output-dir ./results      # Custom output directory
""",
    )
    parser.add_argument("input_file", nargs="?",
                        help="Path to input JSON file")
    parser.add_argument("--example", action="store_true",
                        help="Use the built-in EV charging example")
    parser.add_argument("--json-only", action="store_true",
                        help="Skip HTML report generation")
    parser.add_argument("--no-save", action="store_true",
                        help="Print JSON to stdout, don't write files")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to write output files (default: .)")
    args = parser.parse_args()

    # When stdin is piped (not a TTY), default to --no-save so the CLI
    # contract is pure stdin-json / stdout-json without file side-effects.
    piped = not sys.stdin.isatty()
    if piped and not args.no_save:
        args.no_save = True

    # Load input
    if args.example:
        entry_input = _load_example()
    elif args.input_file:
        entry_input = _load_file(args.input_file)
    elif piped:
        entry_input = _load_stdin()
    else:
        print("No input provided — running built-in EV charging example.",
              file=sys.stderr)
        entry_input = _load_example()

    # Run analysis
    print(f"Running market entry analysis for: {entry_input.market_name}",
          file=sys.stderr)
    scorecard = run_entry_analysis(entry_input)

    # Output
    output_dict = scorecard.model_dump()
    output_dict.pop("html_report", None)
    json_str = json.dumps(output_dict, indent=2)

    if args.no_save:
        print(json_str)
    else:
        _save_outputs(scorecard, Path(args.output_dir), args.json_only)
        print(json_str)


if __name__ == "__main__":
    main()
