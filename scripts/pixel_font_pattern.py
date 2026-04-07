#!/usr/bin/env python3
"""
Pixel Font → Cross-Stitch Converter

Takes an image containing pixel-art text (bitmap font), detects the pixel grid,
extracts the binary on/off pattern, and generates a single-color cross-stitch
chart (PDF + PNG).

Workflow:
  1. Load image, convert to grayscale
  2. Auto-detect pixel grid size (how many real pixels = 1 logical pixel)
  3. Threshold to binary: stitch / empty
  4. Clean up noise (optional morphological ops)
  5. Generate single-color chart with symbol grid, PDF, and PNG

Usage:
  python pixel_font_pattern.py input.png -o font_pattern --color 310 --palette dmc
  python pixel_font_pattern.py input.png -o font_pattern --grid-size 8
"""

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

SCRIPT_DIR = Path(__file__).parent
PALETTES_DIR = SCRIPT_DIR / "palettes"


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


def _load_pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _first_existing_font(
        "dejavu/DejaVuSansMono-Bold.ttf" if bold else "dejavu/DejaVuSansMono.ttf",
        "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
        "ttf/DejaVuSansMono-Bold.ttf" if bold else "ttf/DejaVuSansMono.ttf",
        "consolab.ttf" if bold else "consola.ttf",
    )
    if font_path:
        try:
            return ImageFont.truetype(str(font_path), size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


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
            pdfmetrics.registerFont(TTFont("PixelUnicode", str(regular_path)))
            pdfmetrics.registerFont(TTFont("PixelUnicode-Bold", str(bold_path)))
            return "PixelUnicode", "PixelUnicode-Bold"
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold"


PDF_FONT, PDF_FONT_BOLD = _register_pdf_fonts()


def load_palette(name: str) -> list[dict]:
    path = PALETTES_DIR / f"{name.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(f"Palette not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["colors"]


def find_thread_by_code(palette, code):
    """Find a thread in palette by code (case-insensitive)."""
    code_lower = code.lower()
    for t in palette:
        if t["code"].lower() == code_lower:
            return t
    return None


# ──────────────────────────────────────────
# GRID DETECTION
# ──────────────────────────────────────────

def detect_grid_size(img_gray, max_grid=40):
    """
    Auto-detect the pixel grid size (how many real pixels = 1 logical pixel).
    
    Method: look at horizontal and vertical run-lengths of same-intensity
    regions. The most common run-length (above 1) is likely the grid cell size.
    
    Returns int grid_size (1 if no scaling detected).
    """
    arr = np.array(img_gray)
    h, w = arr.shape
    
    # Threshold to binary first
    threshold = _auto_threshold(arr)
    binary = (arr <= threshold).astype(np.uint8)  # 1 = dark (ink), 0 = light (bg)
    
    run_lengths = Counter()
    
    # Sample horizontal runs from middle rows
    sample_rows = range(h // 4, 3 * h // 4, max(1, h // 30))
    for y in sample_rows:
        current_val = binary[y, 0]
        run_len = 1
        for x in range(1, w):
            if binary[y, x] == current_val:
                run_len += 1
            else:
                if 2 <= run_len <= max_grid:
                    run_lengths[run_len] += 1
                current_val = binary[y, x]
                run_len = 1
        if 2 <= run_len <= max_grid:
            run_lengths[run_len] += 1
    
    # Sample vertical runs from middle columns
    sample_cols = range(w // 4, 3 * w // 4, max(1, w // 30))
    for x in sample_cols:
        current_val = binary[0, x]
        run_len = 1
        for y in range(1, h):
            if binary[y, x] == current_val:
                run_len += 1
            else:
                if 2 <= run_len <= max_grid:
                    run_lengths[run_len] += 1
                current_val = binary[y, x]
                run_len = 1
        if 2 <= run_len <= max_grid:
            run_lengths[run_len] += 1
    
    if not run_lengths:
        return 1
    
    # Find the most common run length — likely the grid cell
    # But also check multiples (e.g., if grid=8 we might see lots of 8, 16, 24)
    candidates = run_lengths.most_common(10)
    
    # Try to find GCD of top candidates
    top_lengths = [c[0] for c in candidates[:5]]
    
    # The smallest frequent run length above 1 is our best guess
    for length, count in sorted(candidates, key=lambda x: x[0]):
        if length >= 2 and count >= max(3, candidates[0][1] * 0.1):
            return length
    
    return candidates[0][0] if candidates else 1


def _auto_threshold(arr):
    """Otsu-like threshold for binary segmentation, with boundary safety."""
    hist, bins = np.histogram(arr.flatten(), bins=256, range=(0, 256))
    total = arr.size
    
    sum_total = np.sum(np.arange(256) * hist)
    sum_bg = 0
    weight_bg = 0
    
    max_variance = 0
    threshold = 128
    
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = t
    
    # For clean bimodal images (e.g. pure pixel art), Otsu often lands
    # exactly on the dark mode. Find the midpoint between the two modes
    # for a safer split.
    dark_mode = threshold
    light_mode = threshold
    for t in range(threshold + 1, 256):
        if hist[t] > 0:
            light_mode = t
            break
    if light_mode > dark_mode:
        threshold = (dark_mode + light_mode) // 2
    
    return threshold


def extract_pixel_grid(img_gray, grid_size, invert=False):
    """
    Downsample the image to logical pixels using the detected grid size.
    Each grid_size × grid_size block → 1 logical pixel (stitch or empty).
    
    Returns binary numpy array: 1 = stitch, 0 = empty.
    """
    arr = np.array(img_gray)
    h, w = arr.shape
    
    # Calculate logical dimensions
    logical_h = h // grid_size
    logical_w = w // grid_size
    
    if logical_h == 0 or logical_w == 0:
        raise ValueError(f"Image too small for grid_size={grid_size}: {w}×{h}")
    
    # Threshold
    threshold = _auto_threshold(arr)
    
    # Downsample by averaging each block
    result = np.zeros((logical_h, logical_w), dtype=np.uint8)
    for ly in range(logical_h):
        for lx in range(logical_w):
            block = arr[
                ly * grid_size : (ly + 1) * grid_size,
                lx * grid_size : (lx + 1) * grid_size
            ]
            mean_val = np.mean(block)
            # Dark = stitch (ink), Light = empty (background)
            result[ly, lx] = 1 if mean_val <= threshold else 0
    
    if invert:
        result = 1 - result
    
    return result


def clean_binary_grid(grid, remove_isolated=True):
    """Remove isolated single pixels (noise)."""
    if not remove_isolated:
        return grid
    
    h, w = grid.shape
    cleaned = grid.copy()
    
    for y in range(h):
        for x in range(w):
            if grid[y, x] == 1:
                # Count neighbors
                neighbors = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny, nx] == 1:
                            neighbors += 1
                # Remove if completely isolated
                if neighbors == 0:
                    cleaned[y, x] = 0
    
    return cleaned


def trim_borders(grid, padding=1):
    """Remove empty borders, keep small padding."""
    rows_with_content = np.any(grid == 1, axis=1)
    cols_with_content = np.any(grid == 1, axis=0)
    
    if not np.any(rows_with_content):
        return grid
    
    row_start = max(0, np.argmax(rows_with_content) - padding)
    row_end = min(grid.shape[0], grid.shape[0] - np.argmax(rows_with_content[::-1]) + padding)
    col_start = max(0, np.argmax(cols_with_content) - padding)
    col_end = min(grid.shape[1], grid.shape[1] - np.argmax(cols_with_content[::-1]) + padding)
    
    return grid[row_start:row_end, col_start:col_end]


# ──────────────────────────────────────────
# OUTPUT GENERATION
# ──────────────────────────────────────────

STITCH_SYMBOL = "●"
EMPTY_SYMBOL = ""

def generate_mono_grid_png(binary_grid, thread_color_rgb, output_path, cell_size=28):
    """
    Generate a readable PNG chart for a single-color pattern.
    Filled cells show the stitch symbol on a colored background.
    Empty cells are white.
    """
    h, w = binary_grid.shape
    margin = 40
    img_w = w * cell_size + margin * 2
    img_h = h * cell_size + margin * 2
    
    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)
    
    sym_font_size = max(10, cell_size - 6)
    label_font_size = max(8, cell_size - 12)
    font_bold = _load_pil_font(sym_font_size, bold=True)
    font_label = _load_pil_font(label_font_size, bold=False)
    
    tr, tg, tb = thread_color_rgb
    # Light tint for filled cells
    bg_r = int(tr * 0.25 + 255 * 0.75)
    bg_g = int(tg * 0.25 + 255 * 0.75)
    bg_b = int(tb * 0.25 + 255 * 0.75)
    
    for y in range(h):
        for x in range(w):
            cx = margin + x * cell_size
            cy = margin + y * cell_size
            
            if binary_grid[y, x] == 1:
                # Filled cell — color tint + symbol
                draw.rectangle(
                    [cx + 1, cy + 1, cx + cell_size - 1, cy + cell_size - 1],
                    fill=(bg_r, bg_g, bg_b)
                )
                bbox = draw.textbbox((0, 0), STITCH_SYMBOL, font=font_bold)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = cx + (cell_size - tw) // 2
                ty = cy + (cell_size - th) // 2 - 1
                draw.text((tx, ty), STITCH_SYMBOL, fill="black", font=font_bold)
    
    # Grid lines
    for x in range(w + 1):
        lx = margin + x * cell_size
        if x % 10 == 0:
            draw.line([(lx, margin - 2), (lx, margin + h * cell_size + 2)],
                      fill="black", width=2)
        else:
            draw.line([(lx, margin), (lx, margin + h * cell_size)],
                      fill="#BBBBBB", width=1)
    for y in range(h + 1):
        ly = margin + y * cell_size
        if y % 10 == 0:
            draw.line([(margin - 2, ly), (margin + w * cell_size + 2, ly)],
                      fill="black", width=2)
        else:
            draw.line([(margin, ly), (margin + w * cell_size, ly)],
                      fill="#BBBBBB", width=1)
    
    # Axis labels
    for x in range(0, w, 10):
        label = str(x)
        draw.text((margin + x * cell_size + 2, margin - label_font_size - 6),
                  label, fill="black", font=font_label)
    for y in range(0, h, 10):
        label = str(y)
        bbox = draw.textbbox((0, 0), label, font=font_label)
        lw = bbox[2] - bbox[0]
        draw.text((margin - lw - 6, margin + y * cell_size + 2),
                  label, fill="black", font=font_label)
    
    img.save(output_path, quality=95)
    return output_path


def generate_mono_preview_png(binary_grid, thread_color_rgb, output_path, cell_size=4):
    """Generate a simple color preview: filled cells in thread color, rest white."""
    h, w = binary_grid.shape
    img = Image.new("RGB", (w * cell_size, h * cell_size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        for x in range(w):
            if binary_grid[y, x] == 1:
                px = x * cell_size
                py = y * cell_size
                draw.rectangle([px, py, px + cell_size - 1, py + cell_size - 1],
                               fill=thread_color_rgb)
    
    img.save(output_path, quality=95)
    return output_path


def generate_mono_pdf(
    binary_grid, thread_info, fabric_count,
    output_path, title="Схема вышивки — пиксельный шрифт",
    preview_path=None
):
    """Generate PDF for a single-color cross-stitch pattern."""
    page_w, page_h = A4
    margin = 15 * mm
    
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "T", parent=styles["Title"], fontName=PDF_FONT_BOLD, fontSize=18, spaceAfter=6*mm, alignment=TA_CENTER)
    heading_style = ParagraphStyle(
        "H", parent=styles["Heading2"], fontName=PDF_FONT_BOLD, fontSize=13, spaceAfter=4*mm, spaceBefore=6*mm)
    body_style = ParagraphStyle(
        "B", parent=styles["Normal"], fontName=PDF_FONT, fontSize=9, spaceAfter=2*mm)
    small_style = ParagraphStyle(
        "S", parent=styles["Normal"], fontName=PDF_FONT, fontSize=7, leading=9)
    
    elements = []
    
    h, w = binary_grid.shape
    total_stitches = int(np.sum(binary_grid))
    size_cm_w = round(w / fabric_count * 2.54, 1)
    size_cm_h = round(h / fabric_count * 2.54, 1)
    
    # Thread consumption
    meters_per_stitch = 0.02 * 1.2  # 2 strands, 20% overhead
    meters = round(total_stitches * meters_per_stitch, 1)
    skeins = math.ceil(meters / 8)
    
    code = thread_info.get("code", "310")
    name = thread_info.get("name", "Black")
    tr = thread_info.get("r", 0)
    tg = thread_info.get("g", 0)
    tb = thread_info.get("b", 0)
    
    # --- Page 1: Info ---
    elements.append(Paragraph(title, title_style))
    
    info = (
        f"<b>Размер:</b> {w} × {h} стежков | "
        f"<b>На ткани {fabric_count} ct:</b> {size_cm_w} × {size_cm_h} см<br/>"
        f"<b>Цвет:</b> 1 — {code} ({name})<br/>"
        f"<b>Всего стежков:</b> {total_stitches}<br/>"
        f"<b>Расход ниток:</b> {meters} м ({skeins} мотк.)<br/>"
        f"<b>Техника:</b> полный крест, один цвет"
    )
    elements.append(Paragraph(info, body_style))
    elements.append(Spacer(1, 4*mm))
    
    # Preview
    if preview_path and os.path.exists(preview_path):
        max_pw = page_w - 2 * margin
        max_ph = 100 * mm
        elements.append(Paragraph("<b>Превью</b>", heading_style))
        elements.append(RLImage(str(preview_path), width=max_pw, height=max_ph,
                                kind="proportional"))
        elements.append(Spacer(1, 4*mm))
    
    # Legend (just one color)
    elements.append(Paragraph("<b>Легенда</b>", heading_style))
    legend_data = [
        ["Символ", "Код", "Название", "Цвет", "Стежки", "Метры", "Мотки"],
        [STITCH_SYMBOL, code, name, "", str(total_stitches), str(meters), str(skeins)]
    ]
    legend_table = Table(legend_data, colWidths=[35, 40, 110, 30, 50, 40, 40])
    legend_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.Color(0.2, 0.2, 0.2)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("BACKGROUND", (3, 1), (3, 1), rl_colors.Color(tr/255, tg/255, tb/255)),
    ]))
    elements.append(legend_table)
    
    # --- Chart pages ---
    elements.append(PageBreak())
    elements.append(Paragraph("<b>Схема</b>", heading_style))
    
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin - 20 * mm
    cell_pdf = 3.5 * mm
    cols_per_page = int(usable_w / cell_pdf)
    rows_per_page = int(usable_h / cell_pdf)
    
    page_num = 0
    for row_start in range(0, h, rows_per_page):
        for col_start in range(0, w, cols_per_page):
            if page_num > 0:
                elements.append(PageBreak())
            page_num += 1
            
            row_end = min(row_start + rows_per_page, h)
            col_end = min(col_start + cols_per_page, w)
            
            label = f"Строки {row_start+1}–{row_end}, Столбцы {col_start+1}–{col_end}"
            elements.append(Paragraph(label, small_style))
            
            chunk_data = []
            header = [""] + [
                str(col_start + c + 1) if (col_start + c) % 5 == 0 else ""
                for c in range(col_end - col_start)
            ]
            chunk_data.append(header)
            
            for r in range(row_start, row_end):
                row_label = str(r + 1) if r % 5 == 0 else ""
                row_data = [row_label]
                for c in range(col_start, col_end):
                    row_data.append(STITCH_SYMBOL if binary_grid[r, c] == 1 else "")
                chunk_data.append(row_data)
            
            n_cols = col_end - col_start + 1
            cell_w = min(cell_pdf, usable_w / n_cols)
            chunk_table = Table(
                chunk_data,
                colWidths=[8*mm] + [cell_w] * (n_cols - 1),
                rowHeights=[4*mm] + [cell_w] * (row_end - row_start)
            )
            
            chunk_styles = [
                ("FONTSIZE", (0, 0), (-1, -1), 5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (1, 1), (-1, -1), 0.3, rl_colors.Color(0.8, 0.8, 0.8)),
                ("FONTSIZE", (0, 0), (0, -1), 4),
                ("FONTSIZE", (0, 0), (-1, 0), 4),
                ("TEXTCOLOR", (0, 0), (0, -1), rl_colors.Color(0.4, 0.4, 0.4)),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.Color(0.4, 0.4, 0.4)),
            ]
            
            # Color filled cells
            stitch_bg = rl_colors.Color(tr/255 * 0.2 + 0.8,
                                         tg/255 * 0.2 + 0.8,
                                         tb/255 * 0.2 + 0.8)
            for ri in range(row_start, row_end):
                for ci in range(col_start, col_end):
                    if binary_grid[ri, ci] == 1:
                        table_r = ri - row_start + 1
                        table_c = ci - col_start + 1
                        chunk_styles.append(
                            ("BACKGROUND", (table_c, table_r),
                             (table_c, table_r), stitch_bg)
                        )
            
            # Bold lines every 10
            for c in range(col_start, col_end + 1):
                if c % 10 == 0:
                    ci = c - col_start + 1
                    if ci <= n_cols - 1:
                        chunk_styles.append(
                            ("LINEAFTER", (ci, 1), (ci, -1), 1, rl_colors.black))
            for r in range(row_start, row_end + 1):
                if r % 10 == 0:
                    ri = r - row_start + 1
                    if ri <= len(chunk_data) - 1:
                        chunk_styles.append(
                            ("LINEBELOW", (1, ri), (-1, ri), 1, rl_colors.black))
            
            chunk_table.setStyle(TableStyle(chunk_styles))
            elements.append(chunk_table)
    
    doc.build(elements)
    return output_path


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pixel font → single-color cross-stitch pattern converter"
    )
    parser.add_argument("image", help="Path to image with pixel text/art")
    parser.add_argument("-o", "--output", default="pixel_pattern",
                        help="Output base name")
    parser.add_argument("--grid-size", type=int, default=0,
                        help="Pixel grid cell size (0 = auto-detect)")
    parser.add_argument("--color", default="310",
                        help="Thread color code (default: 310 = Black)")
    parser.add_argument("-p", "--palette", default="dmc",
                        choices=["dmc", "gamma"],
                        help="Thread palette (default: dmc)")
    parser.add_argument("-f", "--fabric", type=int, default=14,
                        help="Fabric count (default: 14)")
    parser.add_argument("-t", "--title", default="",
                        help="Pattern title")
    parser.add_argument("--invert", action="store_true",
                        help="Invert: stitch the background instead of the text")
    parser.add_argument("--no-trim", action="store_true",
                        help="Don't trim empty borders")
    parser.add_argument("--no-clean", action="store_true",
                        help="Don't remove isolated pixel noise")
    parser.add_argument("--threshold", type=int, default=0,
                        help="Manual brightness threshold 0-255 (0 = auto Otsu)")
    parser.add_argument("--cell-size", type=int, default=28,
                        help="Cell size in pixels for PNG grid (default: 28)")
    parser.add_argument("--output-dir", default=".",
                        help="Output directory")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"Error: image not found: {args.image}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load palette and find thread
    palette = load_palette(args.palette)
    thread = find_thread_by_code(palette, args.color)
    if thread is None:
        print(f"Warning: code '{args.color}' not found in {args.palette} palette, using Black")
        thread = {"code": args.color, "name": "Custom", "r": 0, "g": 0, "b": 0}
    
    thread_rgb = (thread["r"], thread["g"], thread["b"])
    
    # Load image
    print(f"Loading: {args.image}")
    img = Image.open(args.image).convert("L")  # grayscale
    print(f"Image size: {img.size[0]}×{img.size[1]} px")
    
    # Detect grid size
    if args.grid_size > 0:
        grid_size = args.grid_size
        print(f"Grid size (manual): {grid_size}px")
    else:
        grid_size = detect_grid_size(img)
        print(f"Grid size (auto-detected): {grid_size}px")
    
    # Extract logical pixels
    binary = extract_pixel_grid(img, grid_size, invert=args.invert)
    print(f"Logical grid: {binary.shape[1]}×{binary.shape[0]} stitches")
    
    # Clean noise
    if not args.no_clean:
        before = int(np.sum(binary))
        binary = clean_binary_grid(binary)
        after = int(np.sum(binary))
        if before != after:
            print(f"Cleaned {before - after} isolated pixels")
    
    # Trim borders
    if not args.no_trim:
        h_before, w_before = binary.shape
        binary = trim_borders(binary, padding=2)
        h_after, w_after = binary.shape
        if h_before != h_after or w_before != w_after:
            print(f"Trimmed: {w_before}×{h_before} → {w_after}×{h_after}")
    
    h, w = binary.shape
    total_stitches = int(np.sum(binary))
    
    if total_stitches == 0:
        print("Warning: no stitches detected! Try --invert or adjust --threshold")
        sys.exit(1)
    
    title = args.title or f"Пиксельный шрифт — {args.palette.upper()} {thread['code']}"
    
    # Generate outputs
    preview_path = output_dir / f"{args.output}_preview.png"
    print(f"Generating preview: {preview_path}")
    cell_preview = max(2, min(8, 600 // max(w, h)))
    generate_mono_preview_png(binary, thread_rgb, str(preview_path), cell_preview)
    
    grid_path = output_dir / f"{args.output}_grid.png"
    print(f"Generating grid: {grid_path}")
    generate_mono_grid_png(binary, thread_rgb, str(grid_path), args.cell_size)
    
    pdf_path = output_dir / f"{args.output}.pdf"
    print(f"Generating PDF: {pdf_path}")
    generate_mono_pdf(
        binary, thread, args.fabric,
        str(pdf_path), title=title,
        preview_path=str(preview_path)
    )
    
    # Summary
    size_cm_w = round(w / args.fabric * 2.54, 1)
    size_cm_h = round(h / args.fabric * 2.54, 1)
    meters = round(total_stitches * 0.02 * 1.2, 1)
    skeins = math.ceil(meters / 8)
    
    print(f"\n{'='*50}")
    print("PATTERN GENERATED SUCCESSFULLY")
    print(f"{'='*50}")
    print(f"  Size: {w}×{h} stitches")
    print(f"  Fabric {args.fabric}ct: {size_cm_w}×{size_cm_h} cm")
    print(f"  Stitches: {total_stitches}")
    print(f"  Color: {thread['code']} — {thread['name']}")
    print(f"  Thread: {meters}m ({skeins} skeins)")
    print(f"  Grid detected: {grid_size}px per cell")
    print(f"\n  Files:")
    print(f"    PDF:     {pdf_path}")
    print(f"    Grid:    {grid_path}")
    print(f"    Preview: {preview_path}")
    print()


if __name__ == "__main__":
    main()
