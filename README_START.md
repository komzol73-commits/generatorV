Новый чистый `генератор 2` создан на базе клодовского skill.

Состав:
- `scripts/generate_pattern.py`
- `scripts/dmc_gamma_map.py`
- `scripts/pixel_font_pattern.py`
- `scripts/palettes/dmc.json`
- `scripts/palettes/gamma.json`

Это стартовая база для полной переписи генератора без старой сложной логики.

Принцип:
- один linear pipeline
- один source of truth
- минимум скрытых преобразований
- сначала делаем чистую рабочую CLI-основу
- потом, если нужно, добавляем поверх GUI
