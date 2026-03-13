"""Jinja2 HTML report renderer for the Market Entry Attractiveness Agent."""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from schema import EntryScorecard

_TEMPLATE_DIR = Path(__file__).parent
_DOI = "10.1257/0002828041302235"


def _compute_radar_geometry(
    dimensions: list, cx: int = 200, cy: int = 200, r_max: int = 150
) -> tuple[list[dict], str, list[dict]]:
    """Compute axis endpoints, score polygon points, and dot positions for radar chart.

    Returns:
        axis_points: list of {x, y, lx, ly, label} for axis lines and labels
        score_polygon: SVG points string for the score polygon
        score_dots: list of {x, y} for score position dots
    """
    n = len(dimensions)
    axis_points = []
    polygon_pts = []
    score_dots = []

    for i, dim in enumerate(dimensions):
        angle = math.radians(i * 360 / n - 90)
        # Outer axis endpoint
        ax = cx + r_max * math.cos(angle)
        ay = cy + r_max * math.sin(angle)
        # Label position (slightly beyond axis end)
        lx = cx + (r_max + 20) * math.cos(angle)
        ly = cy + (r_max + 20) * math.sin(angle)
        # Truncate label to first word + abbreviation
        label = dim.name if len(dim.name) <= 12 else dim.name[:11] + "\u2026"
        axis_points.append({
            "x": round(ax, 1), "y": round(ay, 1),
            "lx": round(lx, 1), "ly": round(ly, 1),
            "label": label,
        })
        # Score point: invert so score=1 plots at outer edge (favorable), score=5 at center
        r_score = r_max * (6 - dim.score) / 5
        sx = cx + r_score * math.cos(angle)
        sy = cy + r_score * math.sin(angle)
        polygon_pts.append(f"{round(sx,1)},{round(sy,1)}")
        score_dots.append({"x": round(sx, 1), "y": round(sy, 1)})

    return axis_points, " ".join(polygon_pts), score_dots


def render_report(scorecard: EntryScorecard) -> str:
    """Render an EntryScorecard to a self-contained HTML report string."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("template.html")

    axis_points, score_polygon, score_dots = _compute_radar_geometry(scorecard.dimensions)

    return template.render(
        market_name=scorecard.market_name,
        analysis_date=date.today().isoformat(),
        entry_attractiveness_score=scorecard.entry_attractiveness_score,
        verdict=scorecard.verdict.value,
        confidence=scorecard.confidence.value,
        dimensions=scorecard.dimensions,
        critical_risks=scorecard.critical_risks,
        strategic_recommendation=scorecard.strategic_recommendation,
        suggested_entry_mode=scorecard.suggested_entry_mode,
        doi=_DOI,
        axis_points=axis_points,
        score_polygon=score_polygon,
        score_dots=score_dots,
    )
