"""Построение страниц PDF-схемы.

Здесь лежит вся отрисовка листов документа: титул, превью стежков, легенда
и страницы символьной схемы. Модуль отделён от сервисного orchestration-кода.
"""

from __future__ import annotations

import io
import math
import colorsys

from reportlab.lib import colors
from reportlab.lib.units import cm, mm

from .data import DMC_COLORS, DMC_TO_GAMMA
from .fonts import FONT, FONT_BOLD
from .layout import MARGIN, PAGE_H, PAGE_W
from .pattern_core import get_color_rgb, symbol_family, symbols_too_similar
from .render_settings import (
    LEGEND_BRIGHTNESS,
    LEGEND_CONTRAST,
    LEGEND_SATURATION,
    STITCH_RENDER_BRIGHTNESS,
    STITCH_RENDER_CONTRAST,
    STITCH_RENDER_LIGHTEN,
    STITCH_RENDER_SATURATION,
    adjust_rgb01,
)

def _draw_symbol_marker(c, sym, cx, cy, cell, marker_color=(0.05, 0.05, 0.05)):
    """Рисует контрастный маркер в клетке схемы: фигуру, линию или текст."""
    size = cell * 0.62
    half = size / 2
    c.saveState()
    c.setFillColor(colors.Color(*marker_color))
    c.setStrokeColor(colors.Color(*marker_color))

    if sym == "●":
        c.circle(cx, cy, size * 0.26, fill=True, stroke=False)
    elif sym == "○":
        c.setLineWidth(0.9)
        c.circle(cx, cy, size * 0.28, fill=False, stroke=True)
    elif sym == "◉":
        c.circle(cx, cy, size * 0.30, fill=False, stroke=True)
        c.circle(cx, cy, size * 0.14, fill=True, stroke=False)
    elif sym == "◎":
        c.setLineWidth(0.8)
        c.circle(cx, cy, size * 0.30, fill=False, stroke=True)
        c.circle(cx, cy, size * 0.17, fill=False, stroke=True)
    elif sym == "■":
        c.rect(cx - half * 0.72, cy - half * 0.72, half * 1.44, half * 1.44, fill=True, stroke=False)
    elif sym == "□":
        c.setLineWidth(0.9)
        c.rect(cx - half * 0.72, cy - half * 0.72, half * 1.44, half * 1.44, fill=False, stroke=True)
    elif sym == "◆":
        path = c.beginPath()
        path.moveTo(cx, cy + half * 0.85)
        path.lineTo(cx + half * 0.85, cy)
        path.lineTo(cx, cy - half * 0.85)
        path.lineTo(cx - half * 0.85, cy)
        path.close()
        c.drawPath(path, fill=1, stroke=0)
    elif sym == "◇":
        c.setLineWidth(0.9)
        path = c.beginPath()
        path.moveTo(cx, cy + half * 0.85)
        path.lineTo(cx + half * 0.85, cy)
        path.lineTo(cx, cy - half * 0.85)
        path.lineTo(cx - half * 0.85, cy)
        path.close()
        c.drawPath(path, fill=0, stroke=1)
    elif sym == "▲":
        path = c.beginPath()
        path.moveTo(cx, cy + half * 0.9)
        path.lineTo(cx + half * 0.85, cy - half * 0.75)
        path.lineTo(cx - half * 0.85, cy - half * 0.75)
        path.close()
        c.drawPath(path, fill=1, stroke=0)
    elif sym == "△":
        c.setLineWidth(0.9)
        path = c.beginPath()
        path.moveTo(cx, cy + half * 0.9)
        path.lineTo(cx + half * 0.85, cy - half * 0.75)
        path.lineTo(cx - half * 0.85, cy - half * 0.75)
        path.close()
        c.drawPath(path, fill=0, stroke=1)
    elif sym == "+":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.8, cy, cx + half * 0.8, cy)
        c.line(cx, cy - half * 0.8, cx, cy + half * 0.8)
    elif sym == "/":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.75, cy - half * 0.75, cx + half * 0.75, cy + half * 0.75)
    elif sym == "\\":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.75, cy + half * 0.75, cx + half * 0.75, cy - half * 0.75)
    elif sym == "-":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.8, cy, cx + half * 0.8, cy)
    elif sym == "|":
        c.setLineWidth(1.1)
        c.line(cx, cy - half * 0.8, cx, cy + half * 0.8)
    elif sym == "×":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.8, cy - half * 0.8, cx + half * 0.8, cy + half * 0.8)
        c.line(cx - half * 0.8, cy + half * 0.8, cx + half * 0.8, cy - half * 0.8)
    elif sym == "=":
        c.setLineWidth(1.0)
        c.line(cx - half * 0.8, cy - half * 0.22, cx + half * 0.8, cy - half * 0.22)
        c.line(cx - half * 0.8, cy + half * 0.22, cx + half * 0.8, cy + half * 0.22)
    elif sym == "≠":
        c.setLineWidth(1.0)
        c.line(cx - half * 0.75, cy - half * 0.22, cx + half * 0.75, cy - half * 0.22)
        c.line(cx - half * 0.75, cy + half * 0.22, cx + half * 0.75, cy + half * 0.22)
        c.line(cx - half * 0.35, cy - half * 0.7, cx + half * 0.35, cy + half * 0.7)
    elif sym == "÷":
        c.setLineWidth(1.0)
        c.line(cx - half * 0.8, cy, cx + half * 0.8, cy)
        c.circle(cx, cy + half * 0.45, size * 0.07, fill=True, stroke=False)
        c.circle(cx, cy - half * 0.45, size * 0.07, fill=True, stroke=False)
    elif sym == "*":
        c.setLineWidth(1.0)
        c.line(cx - half * 0.75, cy, cx + half * 0.75, cy)
        c.line(cx, cy - half * 0.75, cx, cy + half * 0.75)
        c.line(cx - half * 0.55, cy - half * 0.55, cx + half * 0.55, cy + half * 0.55)
        c.line(cx - half * 0.55, cy + half * 0.55, cx + half * 0.55, cy - half * 0.55)
    elif sym == "#":
        c.setLineWidth(0.9)
        c.line(cx - half * 0.45, cy - half * 0.8, cx - half * 0.2, cy + half * 0.8)
        c.line(cx + half * 0.2, cy - half * 0.8, cx + half * 0.45, cy + half * 0.8)
        c.line(cx - half * 0.8, cy - half * 0.2, cx + half * 0.8, cy - half * 0.2)
        c.line(cx - half * 0.8, cy + half * 0.2, cx + half * 0.8, cy + half * 0.2)
    elif sym == "%":
        c.setLineWidth(0.9)
        c.line(cx - half * 0.7, cy - half * 0.7, cx + half * 0.7, cy + half * 0.7)
        c.circle(cx - half * 0.45, cy + half * 0.45, size * 0.08, fill=False, stroke=True)
        c.circle(cx + half * 0.45, cy - half * 0.45, size * 0.08, fill=False, stroke=True)
    elif sym == "V":
        c.setLineWidth(1.1)
        c.line(cx - half * 0.7, cy + half * 0.55, cx, cy - half * 0.65)
        c.line(cx, cy - half * 0.65, cx + half * 0.7, cy + half * 0.55)
    elif sym == "Z":
        c.setLineWidth(1.0)
        c.line(cx - half * 0.75, cy + half * 0.7, cx + half * 0.75, cy + half * 0.7)
        c.line(cx + half * 0.7, cy + half * 0.7, cx - half * 0.7, cy - half * 0.7)
        c.line(cx - half * 0.75, cy - half * 0.7, cx + half * 0.75, cy - half * 0.7)
    else:
        font_size = min(cell * 0.7 / mm * 2.5, 8)
        c.setFont(FONT_BOLD, font_size)
        c.drawCentredString(cx, cy - cell * 0.18, sym)

    c.restoreState()

def _is_white_family_code(code, rgb):
    """Белые и почти белые оттенки показываем пустой клеткой без символа."""
    code_str = str(code).lower()
    if code_str in {"blanc", "b5200", "white", "3865", "746"}:
        return True
    return all(channel >= 245 for channel in rgb)

def _is_black_family_code(code, rgb):
    """Чёрные и почти чёрные оттенки показываем как полностью залитую клетку."""
    code_str = str(code).lower()
    if code_str in {"310", "black", "3371", "3799"}:
        return True
    return all(channel <= 18 for channel in rgb)

def _is_true_black_code(code):
    """Возвращает True только для базового чёрного цвета, который должен быть чёрным квадратом."""
    return str(code).lower() in {"310", "black"}

def _is_gray_family_code(code, rgb):
    """Серые и малонасыщенные средние оттенки показываем диагональю."""
    spread = max(rgb) - min(rgb)
    avg = sum(rgb) / 3
    return spread <= 18 and 40 <= avg <= 220

def _is_light_family_code(code, rgb):
    """Очень светлые, но не белые оттенки показываем рамкой с точкой."""
    if _is_white_family_code(code, rgb):
        return False
    avg = sum(rgb) / 3
    return avg >= 225

def _get_light_symbol_variant(code, rgb):
    """Возвращает вариант спецмаркера для белых и очень светлых оттенков."""
    code_str = str(code).lower()
    avg = sum(rgb) / 3

    if _is_white_family_code(code, rgb):
        if code_str in {"blanc", "b5200", "white", "3865"} or avg >= 250:
            return "white_outline"
        return "white_empty"

    if _is_light_family_code(code, rgb):
        if avg >= 240:
            return "white_dot"
        return "white_empty"

    return None

def _stable_variant_index(seed, variants_count):
    """Стабильно выбирает вариант спецмаркера по коду цвета и символу."""
    if variants_count <= 0:
        return 0
    return sum(ord(ch) for ch in str(seed)) % variants_count

def _get_gray_symbol_variant(code, rgb):
    """Возвращает вариант спецмаркера для серых и нейтральных оттенков."""
    if not _is_gray_family_code(code, rgb):
        return None

    avg = sum(rgb) / 3
    code_str = str(code).lower()

    if code_str in {"317", "413", "844", "3021", "3787"} or avg < 105:
        return "gray_slash"
    if code_str in {"318", "414", "645", "648", "452"} or avg < 165:
        return "gray_backslash"
    if code_str in {"415", "453", "644", "927", "3743"} or avg >= 200:
        return "gray_hline"
    return "gray_vline"

def _get_special_symbol_variant(code, rgb, sym):
    """Возвращает уникальный визуальный вариант для каждого специального семейства."""
    seed = f"{code}:{sym}"
    avg = sum(rgb) / 3

    if _is_black_family_code(code, rgb):
        variants = ["black_fill", "black_dot", "black_slash", "black_vline", "black_cross"]
        return variants[_stable_variant_index(seed, len(variants))]

    if _is_white_family_code(code, rgb):
        variants = ["white_empty", "white_dot", "white_outline", "white_slash", "white_vline"]
        return variants[_stable_variant_index(seed, len(variants))]

    if _is_light_family_code(code, rgb):
        variants = ["white_dot", "white_outline", "white_slash", "white_backslash", "white_hline", "white_vline", "white_cross"]
        return variants[_stable_variant_index(seed, len(variants))]

    if _is_gray_family_code(code, rgb):
        variants = ["gray_slash", "gray_backslash", "gray_hline", "gray_vline", "gray_cross", "gray_dot"]
        base_variant = _get_gray_symbol_variant(code, rgb)
        preferred = [base_variant] + [variant for variant in variants if variant != base_variant]
        return preferred[_stable_variant_index(seed, len(preferred))]

    if avg >= 190:
        variants = ["white_outline", "white_slash", "white_backslash", "white_hline", "white_vline", "white_cross"]
        return variants[_stable_variant_index(seed, len(variants))]

    if avg >= 125:
        variants = ["gray_slash", "gray_backslash", "gray_hline", "gray_vline", "gray_cross", "gray_dot"]
        return variants[_stable_variant_index(seed, len(variants))]

    variants = ["black_fill", "black_dot", "black_slash", "black_vline", "black_cross"]
    return variants[_stable_variant_index(seed, len(variants))]

def _draw_base_pattern(c, pattern, left, bottom, size):
    """Рисует базовый ч/б паттерн клетки."""
    right = left + size
    top = bottom + size
    inset = size * 0.16
    inner_left = left + inset
    inner_bottom = bottom + inset
    inner_size = size - inset * 2
    cx = left + size / 2
    cy = bottom + size / 2

    if pattern.startswith("black_"):
        c.setFillColor(colors.Color(0.05, 0.05, 0.05))
        c.rect(inner_left, inner_bottom, inner_size, inner_size, fill=True, stroke=False)

    if pattern.startswith("white_"):
        c.setFillColor(colors.white)
        c.rect(inner_left, inner_bottom, inner_size, inner_size, fill=True, stroke=False)

    if pattern in {"white_outline", "white_dot", "white_slash", "white_backslash", "white_hline", "white_vline", "white_cross"}:
        c.setStrokeColor(colors.Color(0.35, 0.35, 0.35))
        c.setLineWidth(0.8 if size >= 10 else 0.45)
        c.rect(inner_left, inner_bottom, inner_size, inner_size, fill=False, stroke=True)

    if pattern == "white_dot":
        c.setFillColor(colors.Color(0.1, 0.1, 0.1))
        c.circle(cx, cy, max(size * 0.10, 0.8), fill=True, stroke=False)
    elif pattern == "white_slash":
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
    elif pattern == "white_backslash":
        c.line(inner_left, inner_bottom + inner_size, inner_left + inner_size, inner_bottom)
    elif pattern == "white_hline":
        c.line(inner_left, cy, inner_left + inner_size, cy)
    elif pattern == "white_vline":
        c.line(cx, inner_bottom, cx, inner_bottom + inner_size)
    elif pattern == "white_cross":
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
        c.line(inner_left, inner_bottom + inner_size, inner_left + inner_size, inner_bottom)
    elif pattern == "gray_slash":
        c.setStrokeColor(colors.Color(0.1, 0.1, 0.1))
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
    elif pattern == "gray_backslash":
        c.setStrokeColor(colors.Color(0.1, 0.1, 0.1))
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(inner_left, inner_bottom + inner_size, inner_left + inner_size, inner_bottom)
    elif pattern == "gray_hline":
        c.setStrokeColor(colors.Color(0.1, 0.1, 0.1))
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(inner_left, cy, inner_left + inner_size, cy)
    elif pattern == "gray_vline":
        c.setStrokeColor(colors.Color(0.1, 0.1, 0.1))
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(cx, inner_bottom, cx, inner_bottom + inner_size)
    elif pattern == "gray_cross":
        c.setStrokeColor(colors.Color(0.1, 0.1, 0.1))
        c.setLineWidth(0.9 if size >= 10 else 0.5)
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
        c.line(inner_left, inner_bottom + inner_size, inner_left + inner_size, inner_bottom)
    elif pattern == "gray_dot":
        c.setStrokeColor(colors.Color(0.25, 0.25, 0.25))
        c.setLineWidth(0.8 if size >= 10 else 0.4)
        c.rect(inner_left, inner_bottom, inner_size, inner_size, fill=False, stroke=True)
        c.setFillColor(colors.Color(0.1, 0.1, 0.1))
        c.circle(cx, cy, max(size * 0.09, 0.7), fill=True, stroke=False)
    elif pattern == "black_dot":
        c.setFillColor(colors.white)
        c.circle(cx, cy, max(size * 0.10, 0.8), fill=True, stroke=False)
    elif pattern == "black_slash":
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
    elif pattern == "black_vline":
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.9 if size >= 10 else 0.55)
        c.line(cx, inner_bottom, cx, inner_bottom + inner_size)
    elif pattern == "black_cross":
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.9 if size >= 10 else 0.5)
        c.line(inner_left, inner_bottom, inner_left + inner_size, inner_bottom + inner_size)
        c.line(inner_left, inner_bottom + inner_size, inner_left + inner_size, inner_bottom)

def _draw_legend_special_symbol(c, code, rgb, sym, x, baseline_y):
    """Рисует символ/спецмаркер в легенде, выровненный по центру строки."""
    marker_y = baseline_y + 2
    if _is_true_black_code(code):
        c.setFillColor(colors.Color(0.05, 0.05, 0.05))
        c.rect(x - 5, marker_y - 5, 10, 10, fill=True, stroke=False)
        return

    if _is_white_family_code(code, rgb):
        _draw_symbol_marker(c, "★", x, marker_y, 7.2)
        return

    _draw_symbol_marker(c, sym, x, marker_y, 12)

def draw_footer(c, page_w, page_h, brand, brand_note, margin=MARGIN):
    """Рисует нижний колонтитул (бренд + копирайт) на текущей странице PDF."""
    c.setFont(FONT, 7)
    c.setFillColor(colors.Color(0.5, 0.5, 0.5))  # серый, чтобы не отвлекал
    footer_text = f"{brand}  —  {brand_note}" if brand_note else brand
    # drawCentredString — рисует строку, центрированную относительно X.
    c.drawCentredString(page_w / 2, margin - 15, footer_text)

def create_title_page(c, title, grid_h, grid_w, n_colors, total_stitches,
                      aida, brand, brand_note, preview_img):
    """Титульная страница PDF: шапка → превью → инфо-блок → список включённого → футер.

    Превью всегда располагается между шапкой и инфо-блоком и масштабируется
    так, чтобы занять всё доступное пространство без искажения пропорций.
    """

    # ----- 1. Шапка страницы (зелёная плашка сверху) -----
    header_h = 80
    c.setFillColor(colors.Color(0.2, 0.3, 0.2))
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 45, title)
    c.setFont(FONT, 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 68, "Cross-stitch pattern PDF")

    # ----- 2. Предварительный расчёт размеров нижней секции -----
    # Считаем физические размеры схемы на канве указанного каунта (aida).
    cm_w = round(grid_w / aida * 2.54, 1)
    cm_h = round(grid_h / aida * 2.54, 1)
    # Добавляем 16 см запаса ткани (по 8 см с каждой стороны).
    canvas_w = round(cm_w + 16, 0)
    canvas_h = round(cm_h + 16, 0)

    # Сводка параметров схемы (пары "Заголовок: значение").
    info_lines = [
        ("Размер:", f"{grid_w} × {grid_h} стежков | на канве {aida} ct: {cm_w} × {cm_h} см"),
        ("Канва:", f"Aida {aida} ct: {int(canvas_w)} × {int(canvas_h)} см (с запасом 8 см)"),
        ("Палитра:", f"{n_colors} цветов (DMC)"),
        ("Всего стежков:", f"{total_stitches:,}"),
        ("Сложность:", "Средняя" if n_colors > 20 else "Начинающий"),
        ("Тип стежка:", "Полный крест (2 нити)"),
    ]
    # Что именно содержится в PDF — формирует блок "Включено".
    includes = [
        "Цветной превью (пиксельный рендер)",
        "Рендер стежков на канве с картой зон",
        "Легенда цветов DMC + Гамма с символами",
        "Цветовая схема с символами",
    ]

    # Высоты блоков: сами рассчитываем, чтобы дальше понять, сколько места
    # осталось под превью.
    info_box_h = len(info_lines) * 22 + 30        # 6 строк по 22pt + внутренние поля
    includes_h = 20 + len(includes) * 16 + 10     # заголовок + строки + отбивка
    separator_h = 15                               # отступ между инфо-блоком и "Включено"
    bottom_section_h = info_box_h + separator_h + includes_h
    footer_margin = 30                             # нижний отступ под футер

    # ----- 3. Превью (растягиваем на всё доступное место над инфо-блоком) -----
    img_top = PAGE_H - header_h - 15                 # верхняя граница превью (15pt под шапкой)
    img_bottom = footer_margin + bottom_section_h + 15  # нижняя граница превью (15pt над инфо)
    avail_h_for_img = img_top - img_bottom           # доступная высота
    avail_w_for_img = PAGE_W - 2 * MARGIN - 40       # доступная ширина (с учётом полей)

    # Рисуем, только если высоты хватает на осмысленную картинку.
    if preview_img and avail_h_for_img > 80:
        # Сохраняем PIL-превью в байтовый буфер в формате PNG — reportlab
        # умеет читать изображения через ImageReader напрямую из буфера.
        buf = io.BytesIO()
        preview_img.save(buf, format='PNG')
        buf.seek(0)
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(buf)

        # Подбираем размеры, сохраняя пропорции схемы.
        aspect = grid_w / grid_h
        img_w_pts = min(avail_w_for_img, avail_h_for_img * aspect)
        img_h_pts = img_w_pts / aspect
        if img_h_pts > avail_h_for_img:
            img_h_pts = avail_h_for_img
            img_w_pts = img_h_pts * aspect

        # Центрируем картинку по горизонтали и по вертикали внутри доступной области.
        x_img = (PAGE_W - img_w_pts) / 2
        y_img = img_bottom + (avail_h_for_img - img_h_pts) / 2

        # Золотистая рамка вокруг превью.
        c.setStrokeColor(colors.Color(0.6, 0.5, 0.3))
        c.setLineWidth(3)
        c.rect(x_img - 5, y_img - 5, img_w_pts + 10, img_h_pts + 10)
        c.drawImage(ir, x_img, y_img, img_w_pts, img_h_pts)

    # ----- 4. Инфо-блок (серый прямоугольник с параметрами схемы) -----
    box_top = footer_margin + bottom_section_h
    box_y = box_top - info_box_h
    c.setFillColor(colors.Color(0.96, 0.96, 0.96))
    c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
    c.setLineWidth(0.5)
    c.roundRect(MARGIN, box_y, PAGE_W - 2 * MARGIN, info_box_h, 4, fill=True, stroke=True)

    # Выводим построчно пары (жирный заголовок + значение обычным шрифтом).
    y = box_y + info_box_h - 22
    for label, value in info_lines:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(colors.Color(0.2, 0.2, 0.2))
        c.drawString(MARGIN + 15, y, label)
        c.setFont(FONT, 9)
        c.drawString(MARGIN + 100, y, value)
        y -= 22

    # ----- 5. Блок "Включено" (перечень страниц PDF) -----
    y_inc = box_y - separator_h
    c.setFont(FONT_BOLD, 9)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    c.drawString(MARGIN + 5, y_inc, "Включено:")
    for item in includes:
        y_inc -= 16
        c.setFont(FONT, 9)
        c.drawString(MARGIN + 20, y_inc, f"→ {item}")

    # ----- 6. Футер и завершение страницы -----
    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()

def create_stitch_render_page(c, title, dmc_grid, color_symbols, stitch_counts,
                               brand, brand_note, cell_size_mm=4.0):
    """Страница 2: имитация стежков на "канве" с картой зон страниц схемы.

    Показывает, как будет выглядеть готовая работа: цвета немного осветляются
    (на 30%), поверх них рисуются красные линии, делящие картинку на зоны,
    соответствующие страницам символьной схемы.
    """
    # ----- Заголовок и пояснение -----
    c.setFont(FONT_BOLD, 11)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    c.drawString(MARGIN, PAGE_H - 40, "Имитация стежков на канве")
    c.setFont(FONT, 8)
    c.drawString(MARGIN, PAGE_H - 55,
                 "Для оценки внешнего вида готовой работы. Линии показывают зоны страниц схемы.")

    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])

    # ----- Подбор размера клетки так, чтобы весь рисунок влез в страницу -----
    avail_w = PAGE_W - 2 * MARGIN - 20
    avail_h = PAGE_H - 100
    cell = min(avail_w / grid_w, avail_h / grid_h)
    total_w = cell * grid_w
    total_h = cell * grid_h
    # Координаты левого нижнего угла "канвы" — центрируем по горизонтали.
    x0 = (PAGE_W - total_w) / 2
    y0 = PAGE_H - 70 - total_h

    # ----- Фон в цвет канвы Aida (бежевый) -----
    c.setFillColor(colors.Color(0.95, 0.93, 0.88))
    c.rect(x0 - 5, y0 - 5, total_w + 10, total_h + 10, fill=True)

    # Насколько осветляем цвета при рендере: 0..1.
    # 0.30 = новое_значение = old + (1 - old) * 0.30 — стремимся к белому.
    LIGHTEN = STITCH_RENDER_LIGHTEN

    # ----- Отрисовка каждой клетки осветлённым цветом -----
    for r in range(grid_h):
        for col in range(grid_w):
            code = dmc_grid[r][col]
            rgb = get_color_rgb(code)
            # Нормализуем 0..255 → 0..1 для reportlab.
            rc, gc, bc = adjust_rgb01(
                (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0),
                brightness=STITCH_RENDER_BRIGHTNESS,
                contrast=STITCH_RENDER_CONTRAST,
                saturation=STITCH_RENDER_SATURATION,
            )
            # Осветляем смешиванием с белым.
            rc = rc + (1.0 - rc) * LIGHTEN
            gc = gc + (1.0 - gc) * LIGHTEN
            bc = bc + (1.0 - bc) * LIGHTEN
            c.setFillColor(colors.Color(min(rc, 1), min(gc, 1), min(bc, 1)))
            # Координаты клетки: ось Y в PDF растёт снизу вверх,
            # поэтому вычитаем строку из total_h.
            px = x0 + col * cell
            py = y0 + total_h - (r + 1) * cell
            c.rect(px, py, cell, cell, fill=True, stroke=False)

    # ----- Расчёт границ зон (должен точь-в-точь совпадать с create_scheme_pages) -----
    scheme_cell = cell_size_mm * mm
    usable_w = PAGE_W - 2 * MARGIN - 20
    usable_h = PAGE_H - 80 - 20
    cols_per_page = int(usable_w / scheme_cell)
    rows_per_page = int(usable_h / scheme_cell)
    n_col_sections = math.ceil(grid_w / cols_per_page)
    n_row_sections = math.ceil(grid_h / rows_per_page)

    # ----- Красные разделительные линии между зонами -----
    c.setStrokeColor(colors.Color(0.8, 0.2, 0.2, 0.7))  # полупрозрачный красный
    c.setLineWidth(1.2)
    # Вертикальные линии — между столбцами зон.
    for cs in range(1, n_col_sections):
        col_boundary = cs * cols_per_page
        if col_boundary < grid_w:
            px = x0 + col_boundary * cell
            c.line(px, y0, px, y0 + total_h)
    # Горизонтальные линии — между строками зон.
    for rs in range(1, n_row_sections):
        row_boundary = rs * rows_per_page
        if row_boundary < grid_h:
            py = y0 + total_h - row_boundary * cell
            c.line(x0, py, x0 + total_w, py)

    # ----- Номера зон в центре каждой зоны (белый кружок + красное число) -----
    page_num = 0
    for row_sec in range(n_row_sections):
        for col_sec in range(n_col_sections):
            page_num += 1
            r_start = row_sec * rows_per_page
            c_start = col_sec * cols_per_page
            r_end = min(r_start + rows_per_page, grid_h)
            c_end = min(c_start + cols_per_page, grid_w)

            # Центр зоны в координатах страницы.
            cx = x0 + (c_start + c_end) / 2 * cell
            cy = y0 + total_h - (r_start + r_end) / 2 * cell

            # saveState/restoreState — изолируем изменения цвета/шрифта.
            c.saveState()
            # Полупрозрачный белый кружок-подложка под номером.
            c.setFillColor(colors.Color(1, 1, 1, 0.7))
            c.circle(cx, cy, 8, fill=True, stroke=False)
            # Красная жирная цифра — номер страницы схемы.
            c.setFillColor(colors.Color(0.7, 0.1, 0.1))
            c.setFont(FONT_BOLD, 7)
            c.drawCentredString(cx, cy - 2.5, str(page_num))
            c.restoreState()

    # ----- Внешняя золотистая рамка -----
    c.setStrokeColor(colors.Color(0.6, 0.5, 0.3))
    c.setLineWidth(2)
    c.rect(x0 - 3, y0 - 3, total_w + 6, total_h + 6, fill=False)

    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()

def _draw_legend_table_header(c, y, headers, col_x):
    """Рисует строку заголовков таблицы легенды."""
    c.setFont(FONT_BOLD, 7)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    for i, header in enumerate(headers):
        c.drawString(col_x[i], y, header)
    y -= 5
    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    return y - 12


def _classify_legend_group(code, rgb):
    """Определяет цветовую группу для легенды."""
    code_str = str(code).lower()
    if code_str.startswith("b:"):
        return "Бленды"
    if _is_black_family_code(code, rgb):
        return "Черные и очень темные"
    if _is_white_family_code(code, rgb):
        return "Белые и почти белые"
    if _is_gray_family_code(code, rgb):
        return "Серые и нейтральные"
    if _is_light_family_code(code, rgb):
        return "Очень светлые оттенки"

    r, g, b = [channel / 255.0 for channel in rgb]
    hue, sat, _ = colorsys.rgb_to_hsv(r, g, b)
    hue_deg = hue * 360

    if sat < 0.18:
        return "Приглушенные и сложные"
    if hue_deg < 18 or hue_deg >= 338:
        return "Красные и розовые"
    if hue_deg < 45:
        return "Оранжевые и персиковые"
    if hue_deg < 70:
        return "Желтые и золотистые"
    if hue_deg < 165:
        return "Зеленые"
    if hue_deg < 250:
        return "Синие и бирюзовые"
    return "Фиолетовые и сиреневые"


def _group_legend_codes(sorted_colors):
    """Группирует цвета по цветовым семействам."""
    group_order = [
        "Бленды",
        "Белые и почти белые",
        "Очень светлые оттенки",
        "Серые и нейтральные",
        "Желтые и золотистые",
        "Оранжевые и персиковые",
        "Красные и розовые",
        "Зеленые",
        "Синие и бирюзовые",
        "Фиолетовые и сиреневые",
        "Черные и очень темные",
        "Приглушенные и сложные",
    ]
    grouped = {name: [] for name in group_order}
    for code in sorted_colors:
        grouped[_classify_legend_group(code, get_color_rgb(code))].append(code)
    return [(name, grouped[name]) for name in group_order if grouped[name]]


def _spread_group_codes(group_codes, color_symbols):
    """Переставляет коды внутри группы, чтобы соседние символы были менее похожи."""
    remaining = list(group_codes)
    arranged = []

    while remaining:
        if not arranged:
            arranged.append(remaining.pop(0))
            continue

        best_index = 0
        best_score = None
        prev_sym = color_symbols[arranged[-1]]
        prev_family = symbol_family(prev_sym)
        prev_prev_sym = color_symbols[arranged[-2]] if len(arranged) > 1 else None
        prev_prev_family = symbol_family(prev_prev_sym) if prev_prev_sym is not None else None

        for idx, code in enumerate(remaining):
            candidate = color_symbols[code]
            candidate_family = symbol_family(candidate)
            score = 0
            if symbols_too_similar(prev_sym, candidate):
                score += 10
            if prev_family is not None and candidate_family == prev_family:
                score += 4
            if prev_prev_sym is not None and symbols_too_similar(prev_prev_sym, candidate):
                score += 3
            if prev_prev_family is not None and candidate_family == prev_prev_family:
                score += 1
            if best_score is None or score < best_score:
                best_score = score
                best_index = idx

        arranged.append(remaining.pop(best_index))

    return arranged


def create_legend_page(c, title, stitch_counts, color_symbols, aida,
                       brand, brand_note):
    """Page 3: DMC Color Legend grouped by color families."""
    headers = ["Цвет", "DMC", "Gamma", "Название", "Стежков", "Нить (м)", "Мотков"]
    col_x = [MARGIN, MARGIN + 35, MARGIN + 80, MARGIN + 140, MARGIN + 290, MARGIN + 375, MARGIN + 440, MARGIN + 495]

    def start_page():
        c.setFont(FONT_BOLD, 11)
        c.setFillColor(colors.Color(0.2, 0.2, 0.2))
        c.drawString(MARGIN, PAGE_H - 40, "Легенда цветов / Условные обозначения")
        return _draw_legend_table_header(c, PAGE_H - 70, headers, col_x)

    y = start_page()
    sorted_colors = sorted(stitch_counts.keys(), key=lambda k: -stitch_counts[k])
    grouped_colors = _group_legend_codes(sorted_colors)
    thread_per_stitch = 0.024

    for group_name, group_codes in grouped_colors:
        group_codes = _spread_group_codes(group_codes, color_symbols)
        if y < 66:
            draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
            c.showPage()
            y = start_page()

        c.setFont(FONT_BOLD, 8)
        c.setFillColor(colors.Color(0.22, 0.22, 0.22))
        c.drawString(MARGIN, y, group_name)
        y -= 10
        c.setStrokeColor(colors.Color(0.82, 0.82, 0.82))
        c.setLineWidth(0.35)
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 10

        for code in group_codes:
            if y < 50:
                draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
                c.showPage()
                y = start_page()
                c.setFont(FONT_BOLD, 8)
                c.setFillColor(colors.Color(0.22, 0.22, 0.22))
                c.drawString(MARGIN, y, group_name)
                y -= 10
                c.setStrokeColor(colors.Color(0.82, 0.82, 0.82))
                c.setLineWidth(0.35)
                c.line(MARGIN, y, PAGE_W - MARGIN, y)
                y -= 10

            sym = color_symbols[code]
            count = stitch_counts[code]
            thread_m = round(count * thread_per_stitch, 1)
            skeins = max(1, math.ceil(thread_m / 8.0))

            if str(code).startswith("b:"):
                c1, c2 = str(code)[2:].split("+")
                _, rgb1 = DMC_COLORS.get(c1, ("?", (128, 128, 128)))
                _, rgb2 = DMC_COLORS.get(c2, ("?", (128, 128, 128)))
                r1, g1, b1 = adjust_rgb01(tuple(v / 255 for v in rgb1), brightness=LEGEND_BRIGHTNESS, contrast=LEGEND_CONTRAST, saturation=LEGEND_SATURATION)
                r2, g2, b2 = adjust_rgb01(tuple(v / 255 for v in rgb2), brightness=LEGEND_BRIGHTNESS, contrast=LEGEND_CONTRAST, saturation=LEGEND_SATURATION)
                c.setFillColor(colors.Color(r1, g1, b1))
                c.rect(col_x[0], y - 4, 6, 12, fill=True, stroke=False)
                c.setFillColor(colors.Color(r2, g2, b2))
                c.rect(col_x[0] + 6, y - 4, 6, 12, fill=True, stroke=False)
                c.setStrokeColor(colors.Color(0.5, 0.5, 0.5))
                c.rect(col_x[0], y - 4, 12, 12, fill=False)
                blend_rgb = tuple((a + b) // 2 for a, b in zip(rgb1, rgb2))
                _draw_legend_special_symbol(c, code, blend_rgb, sym, col_x[0] + 22, y)
                c.setFont(FONT, 7)
                c.drawString(col_x[1], y, f"{c1}+{c2}")
                c.setFillColor(colors.Color(0.3, 0.3, 0.3))
                c.drawString(col_x[2], y, f"{DMC_TO_GAMMA.get(c1, '???')}+{DMC_TO_GAMMA.get(c2, '???')}")
                c.setFillColor(colors.Color(0.1, 0.1, 0.1))
                n1, _ = DMC_COLORS.get(c1, ("?", (0, 0, 0)))
                n2, _ = DMC_COLORS.get(c2, ("?", (0, 0, 0)))
                c.drawString(col_x[3], y, f"Бленд: {n1[:12]}+{n2[:12]}")
            else:
                name_ru, rgb = DMC_COLORS.get(code, ("?", (128, 128, 128)))
                gamma_code = DMC_TO_GAMMA.get(code, "???")
                rc, gc, bc = adjust_rgb01(
                    (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0),
                    brightness=LEGEND_BRIGHTNESS,
                    contrast=LEGEND_CONTRAST,
                    saturation=LEGEND_SATURATION,
                )
                c.setFillColor(colors.Color(rc, gc, bc))
                c.rect(col_x[0], y - 4, 12, 12, fill=True)
                c.setStrokeColor(colors.Color(0.5, 0.5, 0.5))
                c.rect(col_x[0], y - 4, 12, 12, fill=False)
                _draw_legend_special_symbol(c, code, rgb, sym, col_x[0] + 22, y)
                c.setFont(FONT, 7)
                c.drawString(col_x[1], y, str(code))
                c.setFillColor(colors.Color(0.3, 0.3, 0.3))
                c.drawString(col_x[2], y, str(gamma_code))
                c.setFillColor(colors.Color(0.1, 0.1, 0.1))
                c.drawString(col_x[3], y, name_ru[:26])

            c.drawRightString(col_x[4] + 50, y, f"{count:,}")
            c.drawRightString(col_x[5] + 50, y, f"{thread_m}")
            c.drawRightString(col_x[6] + 30, y, str(skeins))
            y -= 14

        y -= 6

    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()

def create_scheme_pages(c, title, dmc_grid, color_symbols, brand, brand_note,
                        cell_size_mm=4.0):
    """Create symbol scheme pages divided into sections."""
    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])
    cell = cell_size_mm * mm

    # Calculate how many cells fit per page
    usable_w = PAGE_W - 2 * MARGIN - 20  # space for row numbers
    usable_h = PAGE_H - 80 - 20  # space for col numbers + header + footer

    cols_per_page = int(usable_w / cell)
    rows_per_page = int(usable_h / cell)

    # How many page sections needed
    n_col_sections = math.ceil(grid_w / cols_per_page)
    n_row_sections = math.ceil(grid_h / rows_per_page)

    page_num = 0
    total_pages = n_row_sections * n_col_sections

    for row_sec in range(n_row_sections):
        for col_sec in range(n_col_sections):
            page_num += 1
            r_start = row_sec * rows_per_page
            r_end = min(r_start + rows_per_page, grid_h)
            c_start = col_sec * cols_per_page
            c_end = min(c_start + cols_per_page, grid_w)

            actual_rows = r_end - r_start
            actual_cols = c_end - c_start

            # Header
            c.setFont(FONT_BOLD, 8)
            c.setFillColor(colors.Color(0.2, 0.2, 0.2))
            c.drawString(MARGIN, PAGE_H - 25, "Символьная схема")
            c.setFont(FONT, 7)
            c.drawString(MARGIN, PAGE_H - 38,
                         f"Строки {r_start + 1}–{r_end}, столбцы {c_start + 1}–{c_end}   |   {page_num}/{total_pages}")

            x0 = MARGIN + 20  # space for row labels
            y0 = PAGE_H - 55

            # Column numbers (every 5)
            c.setFont(FONT, 5)
            c.setFillColor(colors.Color(0.4, 0.4, 0.4))
            for col_idx in range(actual_cols):
                abs_col = c_start + col_idx + 1
                if abs_col % 5 == 1 or abs_col == c_start + 1:
                    px = x0 + col_idx * cell + cell / 2
                    c.drawCentredString(px, y0 + 3, str(abs_col))

            # Draw grid and symbols
            for row_idx in range(actual_rows):
                abs_row = r_start + row_idx + 1
                py = y0 - (row_idx + 1) * cell

                # Row number (every 5)
                if abs_row % 5 == 1 or abs_row == r_start + 1:
                    c.setFont(FONT, 5)
                    c.setFillColor(colors.Color(0.4, 0.4, 0.4))
                    c.drawRightString(x0 - 3, py + cell * 0.25, str(abs_row))

                for col_idx in range(actual_cols):
                    code = dmc_grid[r_start + row_idx][c_start + col_idx]
                    sym = color_symbols[code]
                    rgb = get_color_rgb(code)

                    px = x0 + col_idx * cell

                    # Background color (light tint)
                    rc, gc, bc = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
                    # Make background lighter
                    bg_r = 0.7 + 0.3 * rc
                    bg_g = 0.7 + 0.3 * gc
                    bg_b = 0.7 + 0.3 * bc
                    c.setFillColor(colors.Color(bg_r, bg_g, bg_b))
                    c.rect(px, py, cell, cell, fill=True, stroke=False)

                    # Symbol
                    if _is_true_black_code(code):
                        inset = cell * 0.18
                        c.setFillColor(colors.Color(0.05, 0.05, 0.05))
                        c.rect(px + inset, py + inset, cell - inset * 2, cell - inset * 2, fill=True, stroke=False)
                    elif _is_white_family_code(code, rgb):
                        _draw_symbol_marker(c, "★", px + cell / 2, py + cell / 2, cell * 0.48)
                    else:
                        _draw_symbol_marker(c, sym, px + cell / 2, py + cell / 2, cell)

            # Grid lines
            c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
            c.setLineWidth(0.2)
            for i in range(actual_cols + 1):
                px = x0 + i * cell
                c.line(px, y0, px, y0 - actual_rows * cell)
            for i in range(actual_rows + 1):
                py = y0 - i * cell
                c.line(x0, py, x0 + actual_cols * cell, py)

            # Bold lines every 10
            c.setStrokeColor(colors.Color(0.3, 0.3, 0.3))
            c.setLineWidth(0.8)
            for i in range(actual_cols + 1):
                abs_col = c_start + i
                if abs_col % 10 == 0:
                    px = x0 + i * cell
                    c.line(px, y0, px, y0 - actual_rows * cell)
            for i in range(actual_rows + 1):
                abs_row = r_start + i
                if abs_row % 10 == 0:
                    py = y0 - i * cell
                    c.line(x0, py, x0 + actual_cols * cell, py)

            draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
            c.showPage()
