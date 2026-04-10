"""CLI-слой генератора схем.

Файл отвечает только за разбор аргументов командной строки и передачу уже
подготовленных значений в сервисный слой `service.generate_pattern()`.
"""

from __future__ import annotations

import argparse

from .service import generate_pattern

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-stitch pattern PDF generator")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--width", type=int, default=200, help="Pattern width in stitches")
    parser.add_argument("--max-colors", type=int, default=38, help="Maximum DMC colors")
    parser.add_argument("--title", default="????? ??????? ?????????", help="Pattern title")
    parser.add_argument("--brand", default="???? ???????", help="Brand name")
    parser.add_argument("--brand-note", default="?????? ??? ??????? ?????????????", help="Brand note")
    parser.add_argument("--cell-size", type=float, default=4.0, help="Cell size in mm")
    parser.add_argument("--aida", type=int, default=14, help="Aida count")
    parser.add_argument("--no-oxs", action="store_true", help="Skip OXS file export")
    parser.add_argument("--no-blends", action="store_true", help="Skip blend detection")
    parser.add_argument("--author", default="", help="Author name for PDF/OXS metadata")
    parser.add_argument("--copyright", default="", help="Copyright notice for OXS metadata")
    parser.add_argument("--replace-blend", action="append", default=[], help="Replace blend with solid color, format: 'b:CODE1+CODE2=NEWCODE'")
    parser.add_argument("--replace-region", action="append", default=[], help="Replace color in region, format: 'CODE=NEWCODE:ymin-ymax'")
    return parser

def parse_blend_replacements(items: list[str]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for item in items:
        blend_key, new_code = item.split('=')
        replacements[blend_key] = new_code
    return replacements

def parse_region_replacements(items: list[str]) -> list[dict[str, int | str]]:
    replacements: list[dict[str, int | str]] = []
    for item in items:
        code_part, region_part = item.split(':')
        old_code, new_code = code_part.split('=')
        y_min, y_max = region_part.split('-')
        replacements.append({'old': old_code, 'new': new_code, 'y_min': int(y_min), 'y_max': int(y_max)})
    return replacements

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    generate_pattern(
        args.image,
        args.output,
        target_width=args.width,
        max_colors=args.max_colors,
        title=args.title,
        brand=args.brand,
        brand_note=args.brand_note,
        cell_size_mm=args.cell_size,
        aida=args.aida,
        export_oxs_file=not args.no_oxs,
        author=args.author,
        copyright_note=args.copyright,
        blend_replacements=parse_blend_replacements(args.replace_blend) or None,
        region_replacements=parse_region_replacements(args.replace_region) or None,
        no_blends=args.no_blends,
    )
    return 0
