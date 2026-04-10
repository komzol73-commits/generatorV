#!/usr/bin/env python3
"""Совместимый фасад основного генератора схем.

Этот файл нужен как старый публичный вход в генератор: GUI, CLI и внешние
скрипты могут по-прежнему импортировать его, а настоящая реализация теперь
разложена по модулям пакета `scripts/pattern_generator`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from pattern_generator.cli import main
from pattern_generator.data import ALL_SYMBOLS, DMC_COLORS, DMC_TO_GAMMA, EXTRA_SYMBOLS, SYMBOLS
from pattern_generator.exporters import export_oxs
from pattern_generator.fonts import FONT, FONT_BOLD
from pattern_generator.layout import MARGIN, PAGE_H, PAGE_W
from pattern_generator.pattern_core import (
    detect_blends,
    find_nearest_dmc,
    get_color_rgb,
    image_to_pattern,
    render_stitch_preview,
)
from pattern_generator.pdf_pages import (
    create_legend_page,
    create_scheme_pages,
    create_stitch_render_page,
    create_title_page,
    draw_footer,
)
from pattern_generator.service import generate_pattern

__all__ = [
    "ALL_SYMBOLS",
    "DMC_COLORS",
    "DMC_TO_GAMMA",
    "EXTRA_SYMBOLS",
    "FONT",
    "FONT_BOLD",
    "MARGIN",
    "PAGE_H",
    "PAGE_W",
    "SYMBOLS",
    "create_legend_page",
    "create_scheme_pages",
    "create_stitch_render_page",
    "create_title_page",
    "detect_blends",
    "draw_footer",
    "export_oxs",
    "find_nearest_dmc",
    "generate_pattern",
    "get_color_rgb",
    "image_to_pattern",
    "main",
    "render_stitch_preview",
]

if __name__ == "__main__":
    raise SystemExit(main())
