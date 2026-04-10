"""Регистрация шрифтов для PDF.

Модуль ищет подходящий TTF-шрифт с кириллицей и регистрирует его в ReportLab,
чтобы все PDF-страницы могли использовать единые имена `FONT` и `FONT_BOLD`.
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _font_candidates(*relative_paths: str) -> list[Path]:
    roots: list[Path] = []
    windir = os.environ.get("WINDIR")
    if windir:
        roots.append(Path(windir) / "Fonts")
    roots.extend(
        [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local" / "share" / "fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
        ]
    )

    candidates: list[Path] = []
    seen: set[Path] = set()
    for relative_path in relative_paths:
        rel = Path(relative_path)
        for root in roots:
            candidate = root / rel
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
    return candidates

def _first_existing_font(*relative_paths: str) -> Path | None:
    for candidate in _font_candidates(*relative_paths):
        if candidate.exists():
            return candidate
    return None

def _register_pdf_fonts() -> tuple[str, str]:
    regular_path = _first_existing_font(
        "dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
        "ttf/DejaVuSans.ttf",
        "arial.ttf",
    )
    bold_path = _first_existing_font(
        "dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "ttf/DejaVuSans-Bold.ttf",
        "arialbd.ttf",
    )

    if regular_path and bold_path:
        try:
            pdfmetrics.registerFont(TTFont("AppUnicode", str(regular_path)))
            pdfmetrics.registerFont(TTFont("AppUnicode-Bold", str(bold_path)))
            return "AppUnicode", "AppUnicode-Bold"
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold"

FONT, FONT_BOLD = _register_pdf_fonts()
