"""Настройки цвета для трёх визуальных вариантов схемы.

Значения берутся из активного профиля в ``scripts/color_profiles.json``.
Если файл не найден или профиль не распознан — используются встроенные
значения (профиль «Тёплый (классический)»).

Чтобы добавить профиль — откройте ``color_profiles.json`` и добавьте новый
объект в массив ``profiles``. В GUI появится новая строка в выпадающем списке.

Что за что отвечает:
- canvas_color:
  RGB-цвет фона канвы preview (целые 0..255).
- grid_color_base:
  Базовый RGB сетки на preview (целые 0..255). Проходит через adjust_rgb8.
- stitch_render_bg:
  Фон страницы «Имитация стежков» (float 0..1 для reportlab).
- preview_brightness / preview_contrast / preview_saturation:
  Яркость/контраст/насыщенность stitch-preview (титульная страница + *_preview.png).
- preview_border_width:
  Толщина линий сетки preview; 0 = без сетки.
- preview_grid_brightness / _contrast / _saturation:
  Яркость/контраст/насыщенность самих линий сетки.
- preview_stitch_width_scale:
  Толщина диагоналей крестика (доля от размера клетки).
- preview_stitch_fill_mix:
  Доля цвета канвы, примешиваемая к нити; меньше = чище цвет нити.
- preview_stitch_shadow_strength:
  Сила затемнения нижней диагонали крестика (0..255).
- preview_stitch_highlight_strength:
  Сила высветления верхней диагонали крестика (0..255).
- preview_stitch_inner_pad:
  Отступ крестика от краёв клетки (пикселей).
- preview_stitch_highlight_length:
  Длина локального блика (доля от размера клетки).
- stitch_render_brightness / _contrast / _saturation:
  Параметры страницы «Имитация стежков».
- stitch_render_lighten:
  Степень осветления цветов к белому на странице «Имитация стежков» (0..1).
- legend_brightness / _contrast / _saturation:
  Параметры цветовых плашек в легенде.

Рекомендуемые диапазоны:
- brightness:              0.75 .. 1.25
- contrast:                0.75 .. 1.35
- saturation:              0.60 .. 1.40
- preview_border_width:    0.2 .. 3.0  (0 = выкл)
- preview_stitch_width_scale: 0.30 .. 0.70
- preview_stitch_fill_mix: 0.05 .. 0.40
- preview_stitch_shadow_strength: 8 .. 40
- preview_stitch_highlight_strength: 8 .. 40
- preview_stitch_inner_pad: 1 .. 3
- preview_stitch_highlight_length: 0.20 .. 1.00
- stitch_render_lighten:   0.10 .. 0.45
"""

from __future__ import annotations

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Загрузка активного профиля из color_profiles.json
# ---------------------------------------------------------------------------

def _load_active_profile() -> dict:
    """Читает активный профиль из color_profiles.json рядом со скриптами."""
    profiles_path = Path(__file__).parent.parent / "color_profiles.json"
    if not profiles_path.exists():
        return {}
    try:
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
        active_name = data.get("active", "")
        for profile in data.get("profiles", []):
            if profile.get("name") == active_name:
                return profile
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return {}


_p = _load_active_profile()


# ---------------------------------------------------------------------------
# Цвета холста и сетки (новые константы, управляемые профилем)
# ---------------------------------------------------------------------------

# RGB 0..255 — фон холста в stitch-preview.
CANVAS_COLOR: tuple[int, int, int] = tuple(_p.get("canvas_color", [196, 192, 188]))  # type: ignore[assignment]

# RGB 0..255 — основа цвета сетки preview (передаётся в adjust_rgb8).
GRID_COLOR_BASE: tuple[int, int, int] = tuple(_p.get("grid_color_base", [221, 212, 193]))  # type: ignore[assignment]

# RGB float 0..1 — фон страницы «Имитация стежков» в PDF.
STITCH_RENDER_BG: tuple[float, float, float] = tuple(_p.get("stitch_render_bg", [0.95, 0.93, 0.88]))  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Первая визуализация: stitch-preview на титульной странице и в *_preview.png
# ---------------------------------------------------------------------------

PREVIEW_BRIGHTNESS: float = _p.get("preview_brightness", 1.10)
PREVIEW_CONTRAST: float = _p.get("preview_contrast", 1.02)
PREVIEW_SATURATION: float = _p.get("preview_saturation", 1.26)
PREVIEW_BORDER_WIDTH: float = _p.get("preview_border_width", 0)
PREVIEW_GRID_BRIGHTNESS: float = _p.get("preview_grid_brightness", 1.12)
PREVIEW_GRID_CONTRAST: float = _p.get("preview_grid_contrast", 0.72)
PREVIEW_GRID_SATURATION: float = _p.get("preview_grid_saturation", 0.18)
PREVIEW_STITCH_WIDTH_SCALE: float = _p.get("preview_stitch_width_scale", 0.56)
PREVIEW_STITCH_FILL_MIX: float = _p.get("preview_stitch_fill_mix", 0.12)
PREVIEW_STITCH_SHADOW_STRENGTH: int = int(_p.get("preview_stitch_shadow_strength", 10))
PREVIEW_STITCH_HIGHLIGHT_STRENGTH: int = int(_p.get("preview_stitch_highlight_strength", 21))
PREVIEW_STITCH_INNER_PAD: int = int(_p.get("preview_stitch_inner_pad", 1))
PREVIEW_STITCH_HIGHLIGHT_LENGTH: float = _p.get("preview_stitch_highlight_length", 0.34)

# ---------------------------------------------------------------------------
# Вторая визуализация: страница «Имитация стежков на канве»
# ---------------------------------------------------------------------------

STITCH_RENDER_BRIGHTNESS: float = _p.get("stitch_render_brightness", 1.03)
STITCH_RENDER_CONTRAST: float = _p.get("stitch_render_contrast", 1.10)
STITCH_RENDER_SATURATION: float = _p.get("stitch_render_saturation", 1.12)
STITCH_RENDER_LIGHTEN: float = _p.get("stitch_render_lighten", 0.12)

# ---------------------------------------------------------------------------
# Третья визуализация: цветовые плашки в легенде
# ---------------------------------------------------------------------------

LEGEND_BRIGHTNESS: float = _p.get("legend_brightness", 1.00)
LEGEND_CONTRAST: float = _p.get("legend_contrast", 1.00)
LEGEND_SATURATION: float = _p.get("legend_saturation", 1.00)


# ---------------------------------------------------------------------------
# Вспомогательные функции цветовой коррекции
# ---------------------------------------------------------------------------

def scale_rgb8(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Умножает RGB 0..255 на коэффициент яркости с ограничением диапазона."""
    return tuple(max(0, min(255, int(channel * factor))) for channel in rgb)  # type: ignore[return-value]


def scale_rgb01(rgb: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    """Умножает RGB 0..1 на коэффициент яркости с ограничением диапазона."""
    return tuple(max(0.0, min(1.0, channel * factor)) for channel in rgb)  # type: ignore[return-value]


def apply_saturation_rgb8(rgb: tuple[int, int, int], saturation: float) -> tuple[int, int, int]:
    """Меняет насыщенность RGB 0..255: 1.0 без изменений."""
    r, g, b = rgb
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return tuple(  # type: ignore[return-value]
        max(0, min(255, int(gray + (channel - gray) * saturation)))
        for channel in (r, g, b)
    )


def apply_contrast_rgb8(rgb: tuple[int, int, int], contrast: float) -> tuple[int, int, int]:
    """Меняет контраст RGB 0..255 относительно середины диапазона."""
    return tuple(  # type: ignore[return-value]
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
    return tuple(  # type: ignore[return-value]
        max(0.0, min(1.0, gray + (channel - gray) * saturation))
        for channel in (r, g, b)
    )


def apply_contrast_rgb01(
    rgb: tuple[float, float, float],
    contrast: float,
) -> tuple[float, float, float]:
    """Меняет контраст RGB 0..1 относительно середины диапазона."""
    return tuple(  # type: ignore[return-value]
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
