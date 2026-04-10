"""Тонкая CLI-обёртка для запуска генератора.

Файл сохраняет старую точку входа проекта, а рабочая логика сборки команды
и запуска подпроцесса вынесена в `app.runner`.
"""

from __future__ import annotations

from app.runner import (
    DEFAULT_BRAND,
    DEFAULT_BRAND_NOTE,
    DEFAULT_OUTPUT_DIR,
    build_command,
    build_parser,
    build_subprocess_env,
    main,
    run_generator,
)

__all__ = [
    "DEFAULT_BRAND",
    "DEFAULT_BRAND_NOTE",
    "DEFAULT_OUTPUT_DIR",
    "build_command",
    "build_parser",
    "build_subprocess_env",
    "main",
    "run_generator",
]

if __name__ == "__main__":
    raise SystemExit(main())
