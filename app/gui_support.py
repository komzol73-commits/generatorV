"""Вспомогательные функции для GUI.

Модуль содержит мелкие переиспользуемые утилиты: настройку шрифтов и стилей,
загрузку превью, дописывание лога, расчёт подписей размеров и открытие файлов.
"""

from __future__ import annotations

import json
import os
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import END, ttk

from PIL import Image, ImageTk

# Путь к файлу цветовых профилей
PROFILES_PATH = Path(__file__).resolve().parent.parent / "scripts" / "color_profiles.json"


def resolve_ui_font(root: tk.Misc, preferred: str = "Inter", fallback: str = "Segoe UI") -> str:
    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        available = set()
    return preferred if preferred in available else fallback


def configure_ttk_styles(root: tk.Misc, font_name: str) -> None:
    style = ttk.Style(root)
    style.configure('.', font=(font_name, 10))
    style.configure('TButton', font=(font_name, 10))
    style.configure('TLabel', font=(font_name, 10))
    style.configure('TLabelframe.Label', font=(font_name, 10, 'bold'))
    style.configure('TCheckbutton', font=(font_name, 10))


def load_preview_image(path: Path, max_size: tuple[int, int] = (280, 280)) -> ImageTk.PhotoImage | None:
    if not path.exists():
        return None
    image = Image.open(path).convert('RGB')
    image.thumbnail(max_size)
    return ImageTk.PhotoImage(image)


def append_log(log_widget, text: str) -> None:
    log_widget.configure(state='normal')
    log_widget.insert(END, text + "\n")
    log_widget.see(END)
    log_widget.configure(state='disabled')


def compute_dimension_summary(width: int, aida: int) -> tuple[str, str]:
    width = max(1, width)
    aida = max(1, aida)
    width_cm = round(width / aida * 2.54, 1)
    return (
        f"{width} крестиков по ширине",
        f"Размер на канве {aida} ct: {width_cm} см по ширине",
    )


def open_in_system(path: Path) -> None:
    if os.name == 'nt':
        os.startfile(path)  # type: ignore[attr-defined]


def format_command(command: list[str]) -> str:
    return ' '.join(f'"{part}"' if ' ' in part else part for part in command)


def load_color_profiles() -> tuple[list[str], str]:
    """Возвращает (список имён профилей, имя активного профиля)."""
    if not PROFILES_PATH.exists():
        return [], ""
    try:
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        names = [p["name"] for p in data.get("profiles", []) if "name" in p]
        active = data.get("active", names[0] if names else "")
        return names, active
    except (OSError, json.JSONDecodeError, KeyError):
        return [], ""


def save_active_profile(name: str) -> None:
    """Записывает имя активного профиля в color_profiles.json."""
    if not PROFILES_PATH.exists():
        return
    try:
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        data["active"] = name
        PROFILES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass


def get_profile_description(name: str) -> str:
    """Возвращает описание профиля по его имени, или пустую строку."""
    if not PROFILES_PATH.exists():
        return ""
    try:
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        for p in data.get("profiles", []):
            if p.get("name") == name:
                return p.get("description", "")
    except (OSError, json.JSONDecodeError):
        pass
    return ""
