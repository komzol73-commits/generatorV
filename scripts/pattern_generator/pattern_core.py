"""Ядро подготовки схемы из изображения.

Этот модуль отвечает за конвертацию картинки в сетку крестиков, подбор цветов
DMC, расчёт preview-картинки, работу с блендами и базовые цветовые операции.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans

from .data import ALL_SYMBOLS, DMC_COLORS
from .render_settings import (
    PREVIEW_BRIGHTNESS,
    PREVIEW_BORDER_WIDTH,
    PREVIEW_CONTRAST,
    PREVIEW_GRID_BRIGHTNESS,
    PREVIEW_GRID_CONTRAST,
    PREVIEW_GRID_SATURATION,
    PREVIEW_SATURATION,
    PREVIEW_STITCH_FILL_MIX,
    PREVIEW_STITCH_HIGHLIGHT_STRENGTH,
    PREVIEW_STITCH_HIGHLIGHT_LENGTH,
    PREVIEW_STITCH_INNER_PAD,
    PREVIEW_STITCH_SHADOW_STRENGTH,
    PREVIEW_STITCH_WIDTH_SCALE,
    adjust_rgb8,
)

def find_nearest_dmc(rgb, palette):
    """Находит код DMC-цвета, ближайшего к переданному RGB.

    Используется метрика "квадрат евклидова расстояния" в RGB-пространстве.
    Это не идеально с точки зрения восприятия (лучше было бы Lab/ΔE),
    но быстро и даёт приемлемый результат для схем вышивки.

    Parameters
    ----------
    rgb : tuple[int, int, int]
        Целевой цвет.
    palette : dict[str, tuple[str, tuple[int, int, int]]]
        Палитра в формате {код: (имя, (r, g, b))}.

    Returns
    -------
    str | None
        Код ближайшего цвета DMC.
    """
    min_dist = float('inf')
    best = None
    # Обходим все цвета палитры и ищем минимум квадрата расстояния.
    for code, (name, dmc_rgb) in palette.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, dmc_rgb))
        if dist < min_dist:
            min_dist = dist
            best = code
    return best

def render_stitch_preview(
    dmc_grid,
    cell_px=8,
    brightness=PREVIEW_BRIGHTNESS,
    contrast=PREVIEW_CONTRAST,
    saturation=PREVIEW_SATURATION,
):
    """Собирает preview-картинку с имитацией стежков по DMC-сетке."""
    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0]) if grid_h else 0
    if grid_h == 0 or grid_w == 0:
        return Image.new("RGB", (1, 1), (240, 232, 214))

    render_scale = 2
    cell_px_hr = cell_px * render_scale
    canvas_color = (233, 225, 206)
    preview = Image.new("RGB", (grid_w * cell_px_hr, grid_h * cell_px_hr), canvas_color)
    draw = ImageDraw.Draw(preview)

    inner_pad = max(1, int(round(PREVIEW_STITCH_INNER_PAD * render_scale)))
    shade_offset = max(0, cell_px_hr // 14)
    border_width = max(0, int(round(PREVIEW_BORDER_WIDTH * render_scale)))
    stitch_width = max(1, int(round(cell_px_hr * PREVIEW_STITCH_WIDTH_SCALE)))
    stitch_core_width = max(1, stitch_width - 3)
    highlight_length = max(2, int(round(cell_px_hr * PREVIEW_STITCH_HIGHLIGHT_LENGTH)))
    grid_color = adjust_rgb8(
        (221, 212, 193),
        brightness=PREVIEW_GRID_BRIGHTNESS,
        contrast=PREVIEW_GRID_CONTRAST,
        saturation=PREVIEW_GRID_SATURATION,
    )

    for y, row in enumerate(dmc_grid):
        for x, code in enumerate(row):
            rgb = adjust_rgb8(
                get_color_rgb(code),
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
            )
            x0 = x * cell_px_hr
            y0 = y * cell_px_hr
            x1 = x0 + cell_px_hr - 1
            y1 = y0 + cell_px_hr - 1

            draw.rectangle((x0, y0, x1, y1), fill=canvas_color)

            fill_rgb = tuple(
                int(channel * (1.0 - PREVIEW_STITCH_FILL_MIX) + base * PREVIEW_STITCH_FILL_MIX)
                for channel, base in zip(rgb, canvas_color)
            )

            # Тело крестика строится самими диагоналями, без квадратной подложки.
            shadow_rgb = tuple(max(0, c - PREVIEW_STITCH_SHADOW_STRENGTH) for c in fill_rgb)
            highlight_rgb = tuple(
                min(255, c + PREVIEW_STITCH_HIGHLIGHT_STRENGTH) for c in fill_rgb
            )
            draw.line(
                (x0 + inner_pad, y0 + inner_pad + shade_offset, x1 - inner_pad, y1 - inner_pad + shade_offset),
                fill=shadow_rgb,
                width=stitch_width,
            )
            draw.line(
                (x0 + inner_pad, y0 + inner_pad + shade_offset, x1 - inner_pad, y1 - inner_pad + shade_offset),
                fill=fill_rgb,
                width=stitch_core_width,
            )
            draw.line(
                (x0 + inner_pad, y1 - inner_pad, x1 - inner_pad, y0 + inner_pad),
                fill=fill_rgb,
                width=stitch_width,
            )
            draw.line(
                (x0 + inner_pad, y1 - inner_pad, x1 - inner_pad, y0 + inner_pad),
                fill=fill_rgb,
                width=stitch_core_width,
            )
            # Локальный блик только в верхне-левой части, а не по всей диагонали.
            highlight_x0 = x0 + inner_pad + render_scale
            highlight_y0 = y0 + inner_pad + render_scale
            highlight_x1 = min(x1 - inner_pad, highlight_x0 + highlight_length)
            highlight_y1 = min(y1 - inner_pad, highlight_y0 + highlight_length)
            draw.line(
                (highlight_x0, highlight_y0, highlight_x1, highlight_y1),
                fill=highlight_rgb,
                width=max(1, stitch_core_width - 2),
            )

    # Лёгкая сетка помогает превью выглядеть как канва, а не как сглаженная мозаика.
    if border_width > 0:
        for x in range(0, grid_w * cell_px_hr, cell_px_hr):
            draw.line((x, 0, x, grid_h * cell_px_hr), fill=grid_color, width=border_width)
        for y in range(0, grid_h * cell_px_hr, cell_px_hr):
            draw.line((0, y, grid_w * cell_px_hr, y), fill=grid_color, width=border_width)

    return preview.resize((grid_w * cell_px, grid_h * cell_px), Image.LANCZOS)

def image_to_pattern(image_path, target_width, max_colors):
    """Конвертирует изображение в двумерный "грид" схемы вышивки.

    Алгоритм:
      1) Открываем картинку и приводим к RGB.
      2) Ресайзим до нужной ширины в крестиках (высота — пропорционально).
      3) Кластеризуем все пиксели алгоритмом KMeans (квантование палитры).
      4) Каждый центр кластера привязываем к ближайшему цвету DMC.
      5) По меткам кластеров собираем сетку DMC-кодов.
      6) Считаем стежки по цветам и раздаём символы легенды.

    Returns
    -------
    tuple
        (dmc_grid, stitch_counts, color_symbols, grid_h, grid_w, preview_img)
    """
    # --- 1. Загрузка и ресайз ---
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    # Сохраняем пропорции: target_width задан, высота считается пропорционально.
    target_height = int(target_width * h / w)

    # LANCZOS — качественный фильтр для уменьшения изображения.
    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
    # Разворачиваем картинку в массив пикселей N×3 для KMeans.
    pixels = np.array(img_resized).reshape(-1, 3)

    # --- 2. Квантование цветов через KMeans ---
    # Не имеет смысла просить больше кластеров, чем уникальных пикселей.
    n_colors = min(max_colors, len(set(map(tuple, pixels))))
    # random_state фиксируем, чтобы результат был воспроизводимым.
    # n_init=10 — запускаем алгоритм с 10 разных инициализаций и берём лучший.
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    centroids = kmeans.cluster_centers_.astype(int)  # центры кластеров (RGB)
    labels = kmeans.labels_                           # метка кластера для каждого пикселя

    # --- 3. Привязка центров кластеров к цветам DMC ---
    # Следим, чтобы два центра не привязались к одному и тому же DMC-коду:
    # для этого после каждой привязки исключаем выбранный код из кандидатов.
    dmc_map = {}
    used_codes = set()
    for i, centroid in enumerate(centroids):
        palette_copy = {k: v for k, v in DMC_COLORS.items() if k not in used_codes}
        code = find_nearest_dmc(tuple(centroid), palette_copy)
        dmc_map[i] = code
        used_codes.add(code)

    # --- 4. Сборка итоговой сетки DMC-кодов ---
    grid = labels.reshape(target_height, target_width)
    dmc_grid = [[dmc_map[grid[r][c]] for c in range(target_width)] for r in range(target_height)]

    # --- 5. Подсчёт количества стежков по каждому цвету ---
    stitch_counts = Counter()
    for row in dmc_grid:
        for code in row:
            stitch_counts[code] += 1

    # Сортируем цвета по убыванию частоты — самые массивные получают самые
    # заметные символы (звёздочка, буквы и т.д.).
    sorted_colors = sorted(stitch_counts.keys(), key=lambda c: -stitch_counts[c])

    # --- 6. Назначение символов ---
    # Если цветов больше, чем символов в ALL_SYMBOLS, используем кружки с цифрами
    # из диапазона Unicode (chr(9312) = ①, chr(9313) = ② и т.д.).
    color_symbols = {}
    for i, code in enumerate(sorted_colors):
        color_symbols[code] = ALL_SYMBOLS[i] if i < len(ALL_SYMBOLS) else chr(9312 + i)

    if target_width <= 120:
        preview_cell_px = 10
    elif target_width <= 180:
        preview_cell_px = 8
    else:
        preview_cell_px = 6

    preview_img = render_stitch_preview(
        dmc_grid,
        cell_px=preview_cell_px,
        brightness=PREVIEW_BRIGHTNESS,
        contrast=PREVIEW_CONTRAST,
        saturation=PREVIEW_SATURATION,
    )
    return dmc_grid, stitch_counts, color_symbols, target_height, target_width, preview_img

def detect_blends(dmc_grid, stitch_counts, color_symbols):
    """Находит зоны переходов между двумя цветами и помечает их как бленды.

    Бленды задаются специальным "кодом" формата "b:CODE1+CODE2" (пара отсортирована).
    Такие коды добавляются в stitch_counts и color_symbols рядом с обычными.

    Критерий "это бленд":
      * у пикселя ровно один отличающийся соседний цвет (граница 2 цветов);
      * у пикселя есть хотя бы один сосед того же цвета (не изолированная точка);
      * пара (code1, code2) встречается >= 20 раз (иначе бленд бесполезен).

    Returns
    -------
    tuple[dict, list]
        blend_grid    — {(y, x): (code1, code2)} позиции помеченных блендов;
        sorted_blends — список пар (code1, code2) в порядке убывания частоты.
    """
    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])
    # Словари-накопители: сколько раз встречалась пара и где именно.
    blend_counts = {}     # (code1, code2) -> количество стежков
    blend_positions = {}  # (y, x) -> (code1, code2)

    # --- Первый проход: отмечаем все потенциальные бленды ---
    for y in range(grid_h):
        for x in range(grid_w):
            code = dmc_grid[y][x]
            neighbors = set()
            # Смотрим 4-связных соседей (сверху, снизу, слева, справа).
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < grid_h and 0 <= nx < grid_w:
                    nc = dmc_grid[ny][nx]
                    if nc != code:
                        neighbors.add(nc)
            # Условие "граница ровно двух цветов": есть 1 отличающийся сосед.
            if len(neighbors) == 1:
                other = neighbors.pop()
                pair = tuple(sorted([code, other]))
                # Защита от "одиноких" пикселей: проверим, есть ли хотя бы один
                # сосед того же цвета, что и текущий пиксель.
                same_count = 0
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < grid_h and 0 <= nx < grid_w and dmc_grid[ny][nx] == code:
                        same_count += 1
                if same_count >= 1:
                    blend_counts[pair] = blend_counts.get(pair, 0) + 1
                    blend_positions[(y, x)] = pair

    # --- Фильтрация: оставляем только пары с хотя бы 20 стежками ---
    valid_blends = {p for p, c in blend_counts.items() if c >= 20}
    blend_positions = {pos: pair for pos, pair in blend_positions.items() if pair in valid_blends}

    # Сортируем по популярности, чтобы наиболее часто встречающиеся бленды
    # получили первые (самые заметные) символы.
    sorted_blends = sorted(valid_blends, key=lambda p: -blend_counts[p])
    # Символов для блендов всего 20 (①..⑳) — обрезаем избыток.
    sorted_blends = sorted_blends[:len(BLEND_SYMBOLS)]

    # --- Регистрируем бленды в общих структурах стежков/символов ---
    blend_symbols = {}
    for i, pair in enumerate(sorted_blends):
        key = f"b:{pair[0]}+{pair[1]}"
        blend_symbols[key] = BLEND_SYMBOLS[i]
        stitch_counts[key] = blend_counts[pair]
        color_symbols[key] = BLEND_SYMBOLS[i]

    # Быстрый маппинг пара -> специальный строковый ключ.
    pair_to_key = {pair: f"b:{pair[0]}+{pair[1]}" for pair in sorted_blends}

    # --- Обновляем grid: заменяем обычные коды на "b:..." в позициях блендов ---
    blend_grid = {}
    for (y, x), pair in blend_positions.items():
        if pair in pair_to_key:
            key = pair_to_key[pair]
            blend_grid[(y, x)] = pair
            dmc_grid[y][x] = key
            # Примечание: точный пересчёт stitch_counts для исходных цветов
            # сознательно не делается — небольшая неточность допустима,
            # поскольку счётчики в легенде носят оценочный характер.

    # Лог для оператора — сколько блендов нашли.
    n_blends = len(sorted_blends)
    n_stitches = sum(blend_counts[p] for p in sorted_blends) if sorted_blends else 0
    print(f"Blends: {n_blends} pairs, {n_stitches} stitches")
    return blend_grid, sorted_blends

def get_color_rgb(code):
    """Возвращает RGB для любого кода, в том числе для бленда 'b:X+Y'.

    Для бленда цвет рассчитывается как поканальное среднее двух исходных цветов.
    """
    if str(code).startswith("b:"):
        parts = str(code)[2:].split("+")
        _, rgb1 = DMC_COLORS.get(parts[0], ("?", (128, 128, 128)))
        _, rgb2 = DMC_COLORS.get(parts[1], ("?", (128, 128, 128)))
        # Среднее покомпонентно — целочисленное деление.
        return tuple((a + b) // 2 for a, b in zip(rgb1, rgb2))
    _, rgb = DMC_COLORS.get(code, ("?", (128, 128, 128)))
    return rgb
