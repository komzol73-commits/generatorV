"""Сервисный слой генератора.

Модуль координирует весь pipeline: подготовку изображения, опциональные
замены/бленды, сборку PDF, сохранение preview и экспорт OXS.
"""

from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .exporters import export_oxs
from .pattern_core import build_symbol_priority, detect_blends, image_to_pattern
from .pdf_pages import (
    create_legend_page,
    create_scheme_pages,
    create_stitch_render_page,
    create_title_page,
)

def generate_pattern(image_path, output_path, target_width=200, max_colors=38,
                     title="Схема вышивки крестиком", brand="Твоя вышивка",
                     brand_note="только для личного использования",
                     cell_size_mm=4.0, aida=14,
                     export_oxs_file=True, author="", copyright_note="",
                     blend_replacements=None, region_replacements=None, no_blends=False):
    """Main function: generate complete cross-stitch PDF."""
    print(f"Loading image: {image_path}")
    symbol_priority = build_symbol_priority()
    dmc_grid, stitch_counts, color_symbols, grid_h, grid_w, preview_img = \
        image_to_pattern(image_path, target_width, max_colors)

    total_stitches = sum(stitch_counts.values())
    n_colors = len(stitch_counts)

    print(f"Pattern: {grid_w}x{grid_h} stitches, {n_colors} colors, {total_stitches:,} total")

    # Detect blends
    if no_blends:
        print("Blends: skipped")
        blend_grid, blend_pairs = {}, []
    else:
        print("Detecting blends...")
        blend_grid, blend_pairs = detect_blends(dmc_grid, stitch_counts, color_symbols)

    # Apply color/blend replacements if provided
    if blend_replacements:
        for old_key, replacement_code in blend_replacements.items():
            if old_key in color_symbols:
                sym = color_symbols[old_key]
                count = stitch_counts.get(old_key, 0)
                is_blend = str(old_key).startswith("b:")
                # Replace in grid
                for y in range(grid_h):
                    for x in range(grid_w):
                        if dmc_grid[y][x] == old_key:
                            dmc_grid[y][x] = replacement_code
                # Update counts
                stitch_counts[replacement_code] = stitch_counts.get(replacement_code, 0) + count
                del stitch_counts[old_key]
                del color_symbols[old_key]
                # Assign symbol if new code doesn't have one
                if replacement_code not in color_symbols:
                    used = set(color_symbols.values())
                    for s in symbol_priority:
                        if s not in used:
                            color_symbols[replacement_code] = s
                            break
                if is_blend:
                    # Remove from blend_pairs (list of tuples)
                    pair = tuple(sorted(old_key[2:].split("+")))
                    blend_pairs = [p for p in blend_pairs if p != pair]
                    # Clean blend_grid
                    blend_grid = {pos: val for pos, val in blend_grid.items() if val != pair}
                label = f"blend {sym} ({old_key})" if is_blend else f"color {sym} (DMC {old_key})"
                print(f"Replaced {label} → DMC {replacement_code} ({count} stitches)")

    # Apply region-specific replacements
    if region_replacements:
        for rr in region_replacements:
            old_code = rr['old']
            new_code = rr['new']
            y_min = rr.get('y_min', 0)
            y_max = rr.get('y_max', grid_h - 1)
            old_sym = color_symbols.get(old_code, '?')
            count = 0
            for y in range(y_min, min(y_max + 1, grid_h)):
                for x in range(grid_w):
                    if dmc_grid[y][x] == old_code:
                        dmc_grid[y][x] = new_code
                        count += 1
            if count > 0:
                stitch_counts[old_code] = stitch_counts.get(old_code, 0) - count
                stitch_counts[new_code] = stitch_counts.get(new_code, 0) + count
                if stitch_counts.get(old_code, 0) <= 0:
                    stitch_counts.pop(old_code, None)
                    color_symbols.pop(old_code, None)
                if new_code not in color_symbols:
                    used = set(color_symbols.values())
                    for s in symbol_priority:
                        if s not in used:
                            color_symbols[new_code] = s
                            break
                print(f"Region replace {old_sym} (DMC {old_code}) → DMC {new_code} in rows {y_min}-{y_max} ({count} stitches)")

    c_pdf = canvas.Canvas(output_path, pagesize=A4)
    c_pdf.setTitle(title)
    c_pdf.setAuthor(author if author else brand)

    print("Creating title page...")
    create_title_page(c_pdf, title, grid_h, grid_w, n_colors, total_stitches,
                      aida, brand, brand_note, preview_img)

    print("Creating stitch render page...")
    create_stitch_render_page(c_pdf, title, dmc_grid, color_symbols, stitch_counts,
                               brand, brand_note, cell_size_mm)

    print("Creating legend page...")
    create_legend_page(c_pdf, title, stitch_counts, color_symbols, aida,
                       brand, brand_note)

    print("Creating scheme pages...")
    create_scheme_pages(c_pdf, title, dmc_grid, color_symbols, brand, brand_note,
                        cell_size_mm)

    c_pdf.save()

    preview_path = output_path.rsplit('.', 1)[0] + '_preview.png'
    try:
        preview_img.save(preview_path)
        print(f"Preview saved: {preview_path}")
    except Exception as e:
        print(f"Preview save failed: {e}")

    print(f"Done! Saved to {output_path}")

    # Export OXS file if requested
    if export_oxs_file:
        oxs_path = output_path.rsplit('.', 1)[0] + '.oxs'
        try:
            export_oxs(oxs_path, title, grid_w, grid_h, aida, dmc_grid,
                       stitch_counts, color_symbols, author, copyright_note)
            print(f"OXS exported: {oxs_path}")
        except Exception as e:
            print(f"OXS export failed: {e}")

    return output_path
