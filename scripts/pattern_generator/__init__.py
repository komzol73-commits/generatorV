"""Пакет разложенного ядра генератора схем.

Отсюда удобно импортировать основную функцию `generate_pattern()` и CLI-вход,
не заходя в каждый внутренний модуль по отдельности.
"""

from .service import generate_pattern
from .cli import main
