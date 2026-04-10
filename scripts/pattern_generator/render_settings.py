"""Настройки цвета для трёх визуальных вариантов схемы.

Инструкция:
1. Меняйте числа ниже и сохраняйте файл.
2. После изменения снова собирайте PDF.
3. Каждая настройка отвечает за свой визуальный слой.

Что за что отвечает:
- PREVIEW_BRIGHTNESS:
  первая картинка; это stitch-preview на титульной странице PDF
  и отдельный файл ``*_preview.png``.
- PREVIEW_CONTRAST:
  контраст первой картинки.
- PREVIEW_SATURATION:
  насыщенность первой картинки.
- PREVIEW_BORDER_WIDTH:
  толщина бордера клеток первой картинки.
- STITCH_RENDER_LIGHTEN:
  вторая картинка; это страница "Имитация стежков на канве".
- STITCH_RENDER_BRIGHTNESS:
  общая яркость второй картинки.
- STITCH_RENDER_CONTRAST:
  контраст второй картинки.
- STITCH_RENDER_SATURATION:
  насыщенность второй картинки.
- LEGEND_BRIGHTNESS:
  третья картинка; это цветовые плашки на странице легенды.
- LEGEND_CONTRAST:
  контраст третьей картинки.
- LEGEND_SATURATION:
  насыщенность третьей картинки.

Как понимать значения:
- BRIGHTNESS:
  1.00 = без изменений, меньше 1.00 = темнее, больше 1.00 = ярче.
- CONTRAST:
  1.00 = без изменений, меньше 1.00 = мягче, больше 1.00 = контрастнее.
- SATURATION:
  1.00 = без изменений, меньше 1.00 = бледнее, больше 1.00 = насыщеннее.
- STITCH_RENDER_LIGHTEN:
  0.00 = без осветления, 0.30 = мягкое осветление, больше = светлее.

Рекомендуемые диапазоны:
- PREVIEW_BRIGHTNESS: 0.75 .. 1.25
- PREVIEW_CONTRAST: 0.75 .. 1.35
- PREVIEW_SATURATION: 0.60 .. 1.40
- PREVIEW_BORDER_WIDTH: можно дробное число, но при рендере оно округляется до целого; практически 0.2 .. 3.0
- STITCH_RENDER_BRIGHTNESS: 0.75 .. 1.25
- STITCH_RENDER_CONTRAST: 0.75 .. 1.35
- STITCH_RENDER_SATURATION: 0.60 .. 1.40
- STITCH_RENDER_LIGHTEN: 0.10 .. 0.45
- LEGEND_BRIGHTNESS: 0.75 .. 1.25
- LEGEND_CONTRAST: 0.75 .. 1.35
- LEGEND_SATURATION: 0.60 .. 1.40
"""

from __future__ import annotations

# Первая визуализация: stitch-preview на титульной странице и в *_preview.png.
PREVIEW_BRIGHTNESS = 1.08
PREVIEW_CONTRAST = 0.92
PREVIEW_SATURATION = 1.12
PREVIEW_BORDER_WIDTH = 0

# Вторая визуализация: страница "Имитация стежков на канве".
STITCH_RENDER_BRIGHTNESS = 1.00
STITCH_RENDER_CONTRAST = 1.00
STITCH_RENDER_SATURATION = 1.00
STITCH_RENDER_LIGHTEN = 0.30

# Третья визуализация: цветовые плашки в легенде.
LEGEND_BRIGHTNESS = 1.00
LEGEND_CONTRAST = 1.00
LEGEND_SATURATION = 1.00


def scale_rgb8(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Умножает RGB 0..255 на коэффициент яркости с ограничением диапазона."""
    return tuple(max(0, min(255, int(channel * factor))) for channel in rgb)


def scale_rgb01(rgb: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    """Умножает RGB 0..1 на коэффициент яркости с ограничением диапазона."""
    return tuple(max(0.0, min(1.0, channel * factor)) for channel in rgb)


def apply_saturation_rgb8(rgb: tuple[int, int, int], saturation: float) -> tuple[int, int, int]:
    """Меняет насыщенность RGB 0..255: 1.0 без изменений."""
    r, g, b = rgb
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return tuple(
        max(0, min(255, int(gray + (channel - gray) * saturation)))
        for channel in (r, g, b)
    )


def apply_contrast_rgb8(rgb: tuple[int, int, int], contrast: float) -> tuple[int, int, int]:
    """Меняет контраст RGB 0..255 относительно середины диапазона."""
    return tuple(
        max(0, min(255, int((channel - 128) * contrast + 128)))
        for channel in rgb
    )


def adjust_rgb8(
    rgb: tuple[int, int, int],
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> tuple[int, int, int]:
    """Применяет яркость, контраст и насыщенность к RGB 0..255."""
    rgb = scale_rgb8(rgb, brightness)
    rgb = apply_saturation_rgb8(rgb, saturation)
    rgb = apply_contrast_rgb8(rgb, contrast)
    return rgb


def apply_saturation_rgb01(
    rgb: tuple[float, float, float],
    saturation: float,
) -> tuple[float, float, float]:
    """Меняет насыщенность RGB 0..1: 1.0 без изменений."""
    r, g, b = rgb
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return tuple(
        max(0.0, min(1.0, gray + (channel - gray) * saturation))
        for channel in (r, g, b)
    )


def apply_contrast_rgb01(
    rgb: tuple[float, float, float],
    contrast: float,
) -> tuple[float, float, float]:
    """Меняет контраст RGB 0..1 относительно середины диапазона."""
    return tuple(
        max(0.0, min(1.0, (channel - 0.5) * contrast + 0.5))
        for channel in rgb
    )


def adjust_rgb01(
    rgb: tuple[float, float, float],
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> tuple[float, float, float]:
    """Применяет яркость, контраст и насыщенность к RGB 0..1."""
    rgb = scale_rgb01(rgb, brightness)
    rgb = apply_saturation_rgb01(rgb, saturation)
    rgb = apply_contrast_rgb01(rgb, contrast)
    return rgb
