"""Тонкая точка входа для GUI.

Этот файл нужен только для запуска приложения и обратной совместимости:
основная логика интерфейса живёт в `app.gui`.
"""

from __future__ import annotations

from app.gui import CrossStitchApp, main

__all__ = ["CrossStitchApp", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
