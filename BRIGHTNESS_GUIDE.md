# Настройка яркости

Яркость трёх визуальных вариантов схемы теперь настраивается в одном месте:

- [render_settings.py](/c:/Projects/generatorV/scripts/pattern_generator/render_settings.py)

Что за что отвечает:

- `PREVIEW_BRIGHTNESS`
  Первая картинка.
  Это stitch-preview на титульной странице PDF и файл `*_preview.png`.

- `STITCH_RENDER_LIGHTEN`
  Вторая картинка.
  Это страница `Имитация стежков на канве`.

- `LEGEND_BRIGHTNESS`
  Третья картинка.
  Это цветовые плашки на странице легенды.

Как менять:

1. Откройте [render_settings.py](/c:/Projects/generatorV/scripts/pattern_generator/render_settings.py)
2. Поменяйте число у нужной настройки
3. Сохраните файл
4. Снова соберите PDF

Как понимать значения:

- Для `PREVIEW_BRIGHTNESS` и `LEGEND_BRIGHTNESS`:
  - `1.00` — без изменений
  - `0.85` — темнее
  - `1.15` — ярче

- Для `STITCH_RENDER_LIGHTEN`:
  - `0.00` — без осветления
  - `0.30` — текущий мягкий светлый вариант
  - `0.45` — заметно светлее

Рекомендуемые безопасные диапазоны:

- `PREVIEW_BRIGHTNESS`: от `0.75` до `1.25`
- `STITCH_RENDER_LIGHTEN`: от `0.10` до `0.45`
- `LEGEND_BRIGHTNESS`: от `0.75` до `1.25`
