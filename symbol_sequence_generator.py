"""Отдельный генератор 30 непохожих символов.

Файл никак не встроен в основное приложение. Это самостоятельное окно Tkinter,
в котором символы разбиты по трём размерам и трём категориям:
буквы, геометрические фигуры и дополнительные знаки.
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import BOTH, END, X, ttk
from tkinter.scrolledtext import ScrolledText


LETTER_SYMBOLS = [
    "H", "K", "M", "T", "V", "Q", "R", "U", "Ф", "Ч",
]

GEOMETRIC_SYMBOLS = [
    "■", "●", "▲", "◆", "○", "□", "△", "◇", "★", "☆",
]

EXTRA_SYMBOLS = [
    "4", "7", "9", "@", "#", "%", "&", "+", "=", "|",
]

SIZE_LAYOUT = {
    "large": {"letters": 4, "geometry": 3, "extra": 3},
    "medium": {"letters": 3, "geometry": 4, "extra": 3},
    "small": {"letters": 3, "geometry": 3, "extra": 4},
}

SIZE_ORDER = ["large", "medium", "small"]

SIZE_FONT = {
    "large": ("Segoe UI Symbol", 28, "bold"),
    "medium": ("Segoe UI Symbol", 22, "bold"),
    "small": ("Segoe UI Symbol", 16, "bold"),
}


@dataclass(frozen=True)
class SymbolEntry:
    symbol: str
    category: str
    size: str


def _pick_symbols(pool: list[str], count: int) -> list[str]:
    """Возвращает случайную подвыборку без повторов."""
    if count > len(pool):
        raise ValueError(f"Нельзя выбрать {count} символов из пула размером {len(pool)}.")
    picked = pool[:]
    random.SystemRandom().shuffle(picked)
    return picked[:count]


def generate_symbol_entries() -> list[SymbolEntry]:
    """Генерирует 30 символов: 10 букв, 10 фигур, 10 доп. символов и 10 на каждый размер."""
    letters = _pick_symbols(LETTER_SYMBOLS, 10)
    geometry = _pick_symbols(GEOMETRIC_SYMBOLS, 10)
    extra = _pick_symbols(EXTRA_SYMBOLS, 10)

    letter_index = 0
    geometry_index = 0
    extra_index = 0
    result: list[SymbolEntry] = []

    for size in SIZE_ORDER:
        layout = SIZE_LAYOUT[size]
        for _ in range(layout["letters"]):
            result.append(SymbolEntry(letters[letter_index], "letters", size))
            letter_index += 1
        for _ in range(layout["geometry"]):
            result.append(SymbolEntry(geometry[geometry_index], "geometry", size))
            geometry_index += 1
        for _ in range(layout["extra"]):
            result.append(SymbolEntry(extra[extra_index], "extra", size))
            extra_index += 1

    return result


def generate_distinct_symbol_sequence(count: int = 30) -> list[str]:
    """Совместимая обёртка: возвращает только символы без метаданных."""
    entries = generate_symbol_entries()
    if count != 30:
        return [entry.symbol for entry in entries[:count]]
    return [entry.symbol for entry in entries]


class SymbolSequenceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Генератор 30 символов")
        self.root.geometry("900x560")
        self.root.minsize(820, 500)
        self.current_entries: list[SymbolEntry] = []

        outer = ttk.Frame(root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        ttk.Label(
            outer,
            text="30 символов: 10 больших, 10 средних, 10 маленьких",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="В каждом наборе: 10 букв, 10 геометрических фигур и 10 дополнительных знаков.",
        ).pack(anchor="w", pady=(6, 10))

        ttk.Button(
            outer,
            text="Сгенерировать новую последовательность",
            command=self.generate_sequence,
        ).pack(anchor="w", pady=(0, 10))

        self.output = ScrolledText(outer, height=16, wrap="word", font=("Segoe UI Symbol", 14))
        self.output.pack(fill=X, expand=False)
        self.output.tag_configure("header", font=("Segoe UI", 11, "bold"), spacing1=6, spacing3=4)
        self.output.tag_configure("subtle", font=("Segoe UI", 9), foreground="#666666")
        self.output.tag_configure("large", font=SIZE_FONT["large"])
        self.output.tag_configure("medium", font=SIZE_FONT["medium"])
        self.output.tag_configure("small", font=SIZE_FONT["small"])

        ttk.Button(
            outer,
            text="Скопировать в буфер",
            command=self.copy_to_clipboard,
        ).pack(anchor="w", pady=(10, 0))

        self.generate_sequence()

    def _insert_group(self, title: str, entries: list[SymbolEntry], size_tag: str) -> None:
        self.output.insert(END, f"{title}\n", ("header",))
        self.output.insert(END, "Буквы: ", ("subtle",))
        for entry in entries:
            if entry.category == "letters":
                self.output.insert(END, f"{entry.symbol} ", (size_tag,))
        self.output.insert(END, "\n")

        self.output.insert(END, "Фигуры: ", ("subtle",))
        for entry in entries:
            if entry.category == "geometry":
                self.output.insert(END, f"{entry.symbol} ", (size_tag,))
        self.output.insert(END, "\n")

        self.output.insert(END, "Знаки:  ", ("subtle",))
        for entry in entries:
            if entry.category == "extra":
                self.output.insert(END, f"{entry.symbol} ", (size_tag,))
        self.output.insert(END, "\n\n")

    def generate_sequence(self) -> None:
        self.output.delete("1.0", END)
        self.current_entries = generate_symbol_entries()
        large_entries = [entry for entry in self.current_entries if entry.size == "large"]
        medium_entries = [entry for entry in self.current_entries if entry.size == "medium"]
        small_entries = [entry for entry in self.current_entries if entry.size == "small"]

        self._insert_group("Крупные символы (10)", large_entries, "large")
        self._insert_group("Средние символы (10)", medium_entries, "medium")
        self._insert_group("Маленькие символы (10)", small_entries, "small")

        plain = " ".join(entry.symbol for entry in self.current_entries)
        print(plain)

    def copy_to_clipboard(self) -> None:
        text = " ".join(entry.symbol for entry in self.current_entries)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()


def main() -> int:
    root = tk.Tk()
    SymbolSequenceApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
