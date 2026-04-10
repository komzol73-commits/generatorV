"""Экспорт генератора во внешние форматы.

Сейчас здесь живёт экспорт в OXS. Модуль отделён от PDF-логики, чтобы форматы
вывода не смешивались с кодом построения страниц.
"""

from __future__ import annotations

from .data import DMC_COLORS

def export_oxs(oxs_path, title, width, height, aida, dmc_grid,
               stitch_counts, color_symbols, author="", copyright_note=""):
    """Export pattern in OXS (Open Cross Stitch) format with blend support."""
    import html

    # Separate real DMC codes from blend codes
    all_codes = sorted(stitch_counts.keys(), key=lambda x: -stitch_counts[x])
    real_codes = [c for c in all_codes if not str(c).startswith("b:")]
    blend_codes = [c for c in all_codes if str(c).startswith("b:")]

    # Build index for real codes; ensure blend components are included
    code_to_idx = {}
    for i, code in enumerate(real_codes):
        code_to_idx[code] = i + 1
    for bc in blend_codes:
        for p in str(bc)[2:].split("+"):
            if p not in code_to_idx:
                code_to_idx[p] = len(code_to_idx) + 1

    all_indexed = sorted(code_to_idx.keys(), key=lambda c: code_to_idx[c])
    ascii_syms = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#@$%&*+=-~")
    sym_remap = {code: (ascii_syms[i] if i < len(ascii_syms) else str(i)) for i, code in enumerate(all_indexed)}

    esc = html.escape
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<chart>']

    lines.append('<format comments01="OXS v1.0 with blend/partstitch support" />')
    lines.append(f'<properties oxsversion="1.0" software="Cross-Stitch Generator" software_version="2026" '
        f'chartheight="{height}" chartwidth="{width}" charttitle="{esc(title)}" author="{esc(author)}" '
        f'copyright="{esc(copyright_note)}" stitchesperinch="{aida}" stitchesperinch_y="{aida}" '
        f'palettecount="{len(code_to_idx)}" />')

    lines.append('<palette>')
    lines.append('<palette_item index="0" number="cloth" name="cloth" color="FFFFFF" symbol="" strands="2" />')
    for code in all_indexed:
        idx = code_to_idx[code]
        name_ru, rgb = DMC_COLORS.get(code, ("?", (128,128,128)))
        hx = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        lines.append(f'<palette_item index="{idx}" number="DMC {code}" name="{esc(name_ru)}" '
                     f'color="{hx}" symbol="{sym_remap[code]}" strands="2" />')
    lines.append('</palette>')

    lines.append('<fullstitches>')
    part_lines = []
    for y, row in enumerate(dmc_grid):
        for x, code in enumerate(row):
            sc = str(code)
            if sc.startswith("b:"):
                p = sc[2:].split("+")
                i1, i2 = code_to_idx.get(p[0], 0), code_to_idx.get(p[1], 0)
                part_lines.append(f'<partstitch x="{x}" y="{y}" palindex1="{i1}" palindex2="{i2}" direction="1" />')
            else:
                idx = code_to_idx.get(code, 0)
                if idx > 0:
                    lines.append(f'<stitch x="{x}" y="{y}" palindex="{idx}" />')
    lines.append('</fullstitches>')

    if part_lines:
        lines.append('<partstitches>')
        lines.extend(part_lines)
        lines.append('</partstitches>')

    lines.append('<backstitches />')
    lines.append('</chart>')

    with open(oxs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
