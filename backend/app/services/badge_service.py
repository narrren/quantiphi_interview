"""Shields.io-style flat SVG badges for portfolio metrics."""
from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

DEFAULT_LANGUAGE_COLOR = "#8b949e"
LABEL_COLOR = "#555"
CHAR_WIDTH = 6.5
PADDING = 10
HEIGHT = 20


def compact_number(value: int | float) -> str:
    """1234 -> '1.2K', 268180 -> '268.2K', 2000000 -> '2M'; below 1000 unchanged."""
    n = int(value)
    if abs(n) < 1000:
        return str(n)
    units = ("K", "M", "B")
    scaled, index = n / 1000, 0
    # Round first, then carry so 999_950 becomes "1M" rather than "1000K".
    while abs(round(scaled, 1)) >= 1000 and index < len(units) - 1:
        scaled, index = scaled / 1000, index + 1
    return f"{scaled:.1f}".removesuffix(".0") + units[index]


def _text_width(text: str) -> int:
    return round(len(text) * CHAR_WIDTH) + PADDING


def render_badge(label: str, value: str, color: str) -> str:
    """Render a flat badge: grey label on the left, colored value on the right."""
    lw, vw = _text_width(label), _text_width(value)
    total = lw + vw
    lab, val = escape(label), escape(value)
    col = escape(color, {'"': "&quot;"})
    title = f"{lab}: {val}"
    lx, vx = lw / 2, lw + vw / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{HEIGHT}" '
        f'role="img" aria-label="{escape(f"{label}: {value}", {chr(34): "&quot;"})}">'
        f"<title>{title}</title>"
        '<linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<clipPath id="r"><rect width="{total}" height="{HEIGHT}" rx="3" fill="#fff"/></clipPath>'
        '<g clip-path="url(#r)">'
        f'<rect width="{lw}" height="{HEIGHT}" fill="{LABEL_COLOR}"/>'
        f'<rect x="{lw}" width="{vw}" height="{HEIGHT}" fill="{col}"/>'
        f'<rect width="{total}" height="{HEIGHT}" fill="url(#s)"/></g>'
        '<g fill="#fff" text-anchor="middle" '
        'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{lx}" y="15" fill="#010101" fill-opacity=".3">{lab}</text>'
        f'<text x="{lx}" y="14">{lab}</text>'
        f'<text x="{vx}" y="15" fill="#010101" fill-opacity=".3">{val}</text>'
        f'<text x="{vx}" y="14">{val}</text></g></svg>'
    )


def badge_for(portfolio: dict[str, Any], metric: str) -> tuple[str, str, str]:
    """Return (label, value, color) for a metric of a portfolio."""
    profile = portfolio.get("profile") or {}
    stats = portfolio.get("stats") or {}
    contrib = portfolio.get("contributions") or {}
    if metric == "stars":
        return "GitHub stars", compact_number(stats.get("total_stars") or 0), "#dfb317"
    if metric == "followers":
        return "followers", compact_number(profile.get("followers") or 0), "#2f81f7"
    if metric == "contributions":
        return "contributions (1y)", compact_number(contrib.get("total") or 0), "#2ea043"
    if metric == "streak":
        days = int(contrib.get("longest_streak") or 0)
        return "longest streak", f"{days} day" if days == 1 else f"{days} days", "#f0883e"
    if metric == "top_language":
        languages = [
            lang for lang in stats.get("top_languages") or [] if lang.get("name") != "Other"
        ]
        if not languages:
            return "top language", "n/a", DEFAULT_LANGUAGE_COLOR
        top = languages[0]
        return "top language", top["name"], top.get("color") or DEFAULT_LANGUAGE_COLOR
    raise ValueError(f"Unknown badge metric: {metric}")
